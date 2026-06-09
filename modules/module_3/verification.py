"""
Module 3 - Verifications des caisses.
Persiste en JSON (PostgreSQL optionnel futur).
"""

import json
from pathlib import Path
from datetime import datetime, date
import pandas as pd
from config import logger
from .lecteur_caisse import (
    extraire_numero_caisse,
    lire_montants_caisse,
    to_float,
    trouver_dossier_jour,
    lister_caisses,
)

VERIFICATION_FILE = Path("data/verifications.json")


# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT / SAUVEGARDE
# ══════════════════════════════════════════════════════════════════════════════


def _charger() -> dict:
    """Charge les verifications depuis JSON."""
    if VERIFICATION_FILE.exists():
        try:
            data = json.loads(VERIFICATION_FILE.read_text(encoding="utf-8"))
            logger.debug(f"[MODULE3][VERIF] Verifications chargees")
            return data
        except json.JSONDecodeError as exc:
            logger.error(f"[MODULE3][VERIF] Erreur lecture: {exc}")

    return {}


def _sauvegarder(data: dict):
    """Sauvegarde les verifications en JSON."""
    VERIFICATION_FILE.parent.mkdir(exist_ok=True)
    try:
        VERIFICATION_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        logger.debug("[MODULE3][VERIF] Sauvegarde OK")
    except Exception as exc:
        logger.error(f"[MODULE3][VERIF] Erreur sauvegarde: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# VERIFICATIONS METIER
# ══════════════════════════════════════════════════════════════════════════════


def verifier_montants(df: pd.DataFrame) -> list[str]:
    """
    Verifie que tous les montants sont valides (> 0).

    Args:
        df: DataFrame avec colonnes 'Montant', 'Debit', 'Credit'

    Returns:
        Liste des erreurs
    """
    erreurs = []

    colonnes_montant = [c for c in df.columns if any(m in c for m in ["Montant", "Debit", "Credit"])]

    for col in colonnes_montant:
        for idx, val in enumerate(df[col]):
            montant = to_float(val)
            if montant < 0:
                erreurs.append(f"Ligne {idx + 2}: {col} negatif ({montant})")

    if erreurs:
        logger.warning(f"[MODULE3][VERIF] {len(erreurs)} erreur(s) montant")

    return erreurs


def verifier_dates(df: pd.DataFrame) -> list[str]:
    """
    Verifie que les dates sont valides.

    Args:
        df: DataFrame avec colonne 'Date'

    Returns:
        Liste des erreurs
    """
    erreurs = []

    if "Date" not in df.columns:
        return erreurs

    for idx, val in enumerate(df["Date"]):
        if not _est_date_valide(str(val)):
            erreurs.append(f"Ligne {idx + 2}: Date invalide ({val})")

    if erreurs:
        logger.warning(f"[MODULE3][VERIF] {len(erreurs)} erreur(s) date")

    return erreurs


def verifier_doublons(df: pd.DataFrame) -> list[str]:
    """
    Detecte les doublons sur numero de piece.

    Args:
        df: DataFrame avec colonne 'Piece'

    Returns:
        Liste des doublons detectes
    """
    doublons = []

    if "Piece" not in df.columns:
        return doublons

    pieces = df["Piece"].value_counts()
    for piece, count in pieces.items():
        if count > 1:
            doublons.append(f"Piece {piece}: {count} occurrences")

    if doublons:
        logger.warning(f"[MODULE3][VERIF] {len(doublons)} doublon(s)")

    return doublons


def verifier_caisse(df: pd.DataFrame) -> dict:
    """
    Verifie une caisse complete.

    Args:
        df: DataFrame caisse

    Returns:
        {
            "montants_ok": bool,
            "dates_ok": bool,
            "doublons": list[str],
            "montants_erreurs": list[str],
            "dates_erreurs": list[str],
            "total_lignes": int,
            "total_montant": float,
        }
    """
    erreurs_montant = verifier_montants(df)
    erreurs_date = verifier_dates(df)
    doublons = verifier_doublons(df)

    total_montant = 0.0
    if "Montant" in df.columns:
        total_montant = df["Montant"].apply(to_float).sum()

    return {
        "montants_ok": len(erreurs_montant) == 0,
        "dates_ok": len(erreurs_date) == 0,
        "doublons": doublons,
        "montants_erreurs": erreurs_montant,
        "dates_erreurs": erreurs_date,
        "total_lignes": len(df),
        "total_montant": total_montant,
    }


def verifier_caisses(date_caisse: date) -> dict:
    """
    Verifie toutes les caisses d'une date.

    Args:
        date_caisse: datetime.date

    Returns:
        {
            "date": "2026-06-02",
            "caisses": {
                "01": {...},
                "02": {...},
            },
            "resume": {
                "total": 5,
                "ok": 3,
                "erreurs": 2,
            }
        }
    """
    dossier_jour = trouver_dossier_jour(date_caisse)
    if not dossier_jour:
        logger.warning(f"[MODULE3][VERIF] Aucun dossier pour {date_caisse}")
        return {"date": str(date_caisse), "caisses": {}, "resume": {"total": 0, "ok": 0, "erreurs": 0}}

    fichiers_caisses = lister_caisses(dossier_jour)
    result = {
        "date": str(date_caisse),
        "caisses": {},
        "resume": {"total": 0, "ok": 0, "erreurs": 0},
    }

    for chemin_caisse in fichiers_caisses:
        numero = extraire_numero_caisse(chemin_caisse)
        montants = lire_montants_caisse(chemin_caisse)

        # Convertir en DataFrame simple
        df = pd.DataFrame([montants["montants"]])
        verif = verifier_caisse(df)

        result["caisses"][numero] = verif
        result["resume"]["total"] += 1

        if verif["montants_ok"] and verif["dates_ok"] and not verif["doublons"]:
            result["resume"]["ok"] += 1
        else:
            result["resume"]["erreurs"] += 1

    logger.info(f"[MODULE3][VERIF] Resume: {result['resume']['ok']}/{result['resume']['total']} OK")

    return result


def generer_rapport_verification() -> pd.DataFrame:
    """
    Genere un rapport de verification complet.

    Returns:
        DataFrame avec colonnes: Date, Caisse, Statut, Details
    """
    data = _charger()
    rows = []

    for date_str, info in data.items():
        if isinstance(info, dict) and "caisses" in info:
            for num_caisse, verif in info["caisses"].items():
                statut = "OK" if verif.get("montants_ok") else "ERREUR"
                details = ", ".join(verif.get("montants_erreurs", [])[:2])

                rows.append({
                    "Date": date_str,
                    "Caisse": num_caisse,
                    "Statut": statut,
                    "Details": details,
                    "Montant": verif.get("total_montant", 0.0),
                })

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SAUVEGARDE / CHARGEMENT VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════


def sauvegarder_verification(date_caisse: date, verif: dict):
    """
    Sauvegarde la verification d'une date.

    Args:
        date_caisse: datetime.date
        verif: dict de verification
    """
    data = _charger()
    jour_str = date_caisse.strftime("%Y-%m-%d")
    data[jour_str] = verif
    _sauvegarder(data)
    logger.info(f"[MODULE3][VERIF] Verification {jour_str} sauvegardee")


def charger_verification(date_caisse: date | str) -> dict | None:
    """
    Charge la verification d'une date.

    Args:
        date_caisse: datetime.date ou str "YYYY-MM-DD" ou "JJ/MM/AAAA"

    Returns:
        dict ou None
    """
    # Normaliser la date
    if isinstance(date_caisse, date):
        jour_str = date_caisse.strftime("%Y-%m-%d")
    elif isinstance(date_caisse, str):
        jour_str = _normaliser_date(date_caisse)
    else:
        logger.error(f"[MODULE3][VERIF] Type date invalide: {type(date_caisse)}")
        return None

    data = _charger()
    verif = data.get(jour_str)

    if verif:
        logger.debug(f"[MODULE3][VERIF] Verification {jour_str} chargee")

    return verif


def recalculer_totaux_verification(date_caisse: date | str) -> dict:
    """
    Recalcule les totaux d'une verification sauvegardee.

    Args:
        date_caisse: datetime.date ou str

    Returns:
        dict de verification mis a jour
    """
    if isinstance(date_caisse, str):
        # Parser la date
        try:
            jour_str = _normaliser_date(date_caisse)
            date_caisse = datetime.strptime(jour_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"[MODULE3][VERIF] Date invalide: {date_caisse}")
            return {}

    verif = verifier_caisses(date_caisse)
    sauvegarder_verification(date_caisse, verif)

    return verif


# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════


def _normaliser_date(date_str: str) -> str:
    """
    Convertit une date en "YYYY-MM-DD".

    Accepte: "JJ/MM/AAAA", "DD-MM-YYYY", "YYYY-MM-DD"

    Args:
        date_str: str date

    Returns:
        str au format "YYYY-MM-DD" ou date_str si parse fail
    """
    date_str = date_str.strip()

    # Essayer JJ/MM/AAAA
    try:
        j, m, a = date_str.split("/")
        return f"{a}-{m}-{j}"
    except (ValueError, IndexError):
        pass

    # Essayer DD-MM-YYYY
    try:
        j, m, a = date_str.split("-")
        if len(a) == 4:
            return f"{a}-{m}-{j}"
    except (ValueError, IndexError):
        pass

    logger.warning(f"Format date invalide: {date_str}")
    return date_str


def _est_date_valide(date_str: str) -> bool:
    """Verifie qu'une date est valide."""
    try:
        date_norm = _normaliser_date(date_str)
        a, m, j = map(int, date_norm.split("-"))
        if 1 <= m <= 12 and 1 <= j <= 31 and a >= 2000:
            return True
    except (ValueError, IndexError):
        pass
    return False


def charger_verification_simple(date_caisse: str) -> dict:
    """
    Alias simple pour charger_verification (compatibilite).

    Args:
        date_caisse: date au format "JJ/MM/AAAA" ou "YYYY-MM-DD"

    Returns:
        dict ou {}
    """
    result = charger_verification(date_caisse)
    return result if result else {}


__all__ = [
    "sauvegarder_verification",
    "charger_verification",
    "charger_verification_simple",
    "recalculer_totaux_verification",
    "verifier_montants",
    "verifier_dates",
    "verifier_doublons",
    "verifier_caisse",
    "verifier_caisses",
    "generer_rapport_verification",
]
