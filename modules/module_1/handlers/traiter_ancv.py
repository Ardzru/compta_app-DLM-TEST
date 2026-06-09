"""
Module 1 - Handler ANCV
Logique métier identique à l'original, adaptée au nouveau core.
"""

from pathlib import Path
from collections import defaultdict
from typing import Optional
import pandas as pd

from config import DOSSIER_SORTIE, logger
from core.utils.montant import format_montant_compta
from core.utils.constantes import (
    STE_DLM,
    JOURNAL_CEBOOBA,
    AUXILIAIRE_VIDE,
    ANALYTIQUE_VIDE,
    COL_STE, COL_DATE, COL_COMPTE, COL_AUX,
    COL_PIECE, COL_OBJET, COL_DEBIT, COL_CREDIT,
    COL_JOURNAL, COL_ANALYTIQUE,
    COLONNES_SORTIE,
)

# ==========================================================
# COLONNES ATTENDUES DANS LE FICHIER SOURCE
# ==========================================================
COL_ETAT     = "EtatANCV"
COL_FINALISE = "Transaction Finalisée"
COL_MONTANT  = "CVCo"
COL_DATE_SRC = "Date de création(UTC)"
COL_REFERENCE= "Order Id"

# Comptes comptables ANCV
COMPTE_ANCV_INTERNET = "580010DS5"
COMPTE_ANCV_CAISSE   = "580004"

# ==========================================================
# UTILITAIRES INTERNES
# ==========================================================

def _nettoyer_montant(val) -> float:
    try:
        return float(str(val).replace(",", ".").replace(" ", "").strip())
    except (ValueError, TypeError):
        logger.warning(f"[ANCV] Montant invalide ignoré : {val!r}")
        return 0.0


def _formater_date(val) -> Optional[str]:
    v = str(val).strip()
    if not v or v.upper() in ("NAN", "NONE"):
        return None
    d = pd.to_datetime(v, dayfirst=True, errors="coerce")
    if pd.isna(d):
        logger.warning(f"[ANCV] Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d/%m/%Y")


def _compte_et_piece(reference: str, date: str) -> tuple[str, str]:
    """Order Id à 8 chiffres → Internet, sinon Caisse."""
    ref_clean = str(reference).strip()
    if len(ref_clean) == 8 and ref_clean.isdigit():
        return COMPTE_ANCV_INTERNET, f"ANCV connect Internet du {date}"
    return COMPTE_ANCV_CAISSE, f"ANCV connect Caisse du {date}"


def _est_finalise(val) -> bool:
    v = str(val).strip().upper()
    if v in ("", "NAN", "FALSE", "NONE"):
        return False
    if v == "TRUE":
        return True
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    return not pd.isna(d)


def _est_validated(val) -> bool:
    v = str(val).strip().upper()
    return v in ("VALIDATED", "TRUE")


# ==========================================================
# CORRECTION DU FICHIER (12 colonnes → 11)
# ==========================================================

def _corriger_fichier_ancv(fichier: Path) -> pd.DataFrame:
    """Supprime le point-virgule final parasite de chaque ligne."""
    with open(fichier, "r", encoding="utf-8-sig") as f:
        lignes = f.readlines()

    lignes_corrigees = []
    for ligne in lignes:
        ligne = ligne.rstrip()
        if ligne.endswith(";"):
            ligne = ligne[:-1]
        lignes_corrigees.append(ligne)

    fichier_temp = fichier.with_suffix(".csv.temp")
    with open(fichier_temp, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lignes_corrigees))

    df = pd.read_csv(fichier_temp, sep=";", dtype=str, encoding="utf-8-sig")

    if "Unnamed: 11" in df.columns:
        df = df.drop(columns=["Unnamed: 11"])

    df = df.dropna(how="all")
    fichier_temp.unlink()
    return df


# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_ancv(fichier: Path) -> tuple[str, str]:
    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier ANCV introuvable : {fichier}")

    logger.info(f"[ANCV] Traitement : {fichier.name}")

    # 1. Lecture + correction
    try:
        df = _corriger_fichier_ancv(fichier)
    except Exception as e:
        raise ValueError(f"[ANCV] Échec correction fichier : {e}") from e

    # 2. Vérification colonnes
    colonnes_requises = {COL_ETAT, COL_FINALISE, COL_MONTANT, COL_DATE_SRC, COL_REFERENCE}
    manquantes = colonnes_requises - set(df.columns)
    if manquantes:
        raise ValueError(f"[ANCV] Colonnes manquantes : {manquantes}")

    logger.info(f"[ANCV] Colonnes : {list(df.columns)}")
    logger.info(f"[ANCV] {COL_DATE_SRC} exemples : {df[COL_DATE_SRC].head(3).tolist()}")
    logger.info(f"[ANCV] {COL_REFERENCE} exemples : {df[COL_REFERENCE].head(3).tolist()}")
    logger.info(f"[ANCV] {COL_MONTANT} exemples : {df[COL_MONTANT].head(3).tolist()}")

    # 3. Filtrage
    df = df[df[COL_ETAT].apply(_est_validated)]
    logger.info(f"[ANCV] VALIDATED : {len(df)}")

    df = df[df[COL_FINALISE].apply(_est_finalise)]
    logger.info(f"[ANCV] Finalisées : {len(df)}")

    df[COL_MONTANT] = df[COL_MONTANT].apply(_nettoyer_montant)
    df = df[df[COL_MONTANT] > 0]
    logger.info(f"[ANCV] Montant > 0 : {len(df)}")

    if len(df) == 0:
        logger.warning(f"[ANCV] Aucune ligne valide dans {fichier.name}")
        return "ERREUR", "Aucune ligne valide"

    # 4. Groupement par (date, compte)
    groupes = defaultdict(lambda: {"lignes": [], "total": 0.0})

    for _, row in df.iterrows():
        date = _formater_date(row[COL_DATE_SRC])
        if not date:
            logger.warning(f"[ANCV] Ligne ignorée : date invalide ({row[COL_DATE_SRC]!r})")
            continue

        montant   = float(row[COL_MONTANT])
        reference = str(row[COL_REFERENCE]).strip()
        compte, piece = _compte_et_piece(reference, date)

        groupes[(date, compte)]["lignes"].append({
            COL_STE:        STE_DLM,
            COL_DATE:       date,
            COL_COMPTE:     compte,
            COL_AUX:        AUXILIAIRE_VIDE,
            COL_PIECE:      piece,
            COL_OBJET:      reference,
            COL_DEBIT:      "",
            COL_CREDIT:     format_montant_compta(montant),  # ex: "150,59"
            COL_JOURNAL:    JOURNAL_CEBOOBA,
            COL_ANALYTIQUE: ANALYTIQUE_VIDE,
        })
        groupes[(date, compte)]["total"] += montant

    # 5. Lignes de contrepartie (débit total)
    lignes_finales = []

    for (date, compte), groupe in sorted(groupes.items()):
        lignes_finales.extend(groupe["lignes"])

        total = round(groupe["total"], 2)
        if total == 0.0:
            logger.warning(f"[ANCV] Total nul pour ({date}, {compte}), ignoré")
            continue

        _, piece = _compte_et_piece(
            "12345678" if compte == COMPTE_ANCV_INTERNET else "X",
            date,
        )

        lignes_finales.append({
            COL_STE:        STE_DLM,
            COL_DATE:       date,
            COL_COMPTE:     compte,
            COL_AUX:        AUXILIAIRE_VIDE,
            COL_PIECE:      piece,
            COL_OBJET:      piece,
            COL_DEBIT:      format_montant_compta(total),   # ex: "150,59"
            COL_CREDIT:     "",
            COL_JOURNAL:    JOURNAL_CEBOOBA,
            COL_ANALYTIQUE: ANALYTIQUE_VIDE,
        })

    # 6. Export CSV
    if not lignes_finales:
        logger.warning(f"[ANCV] Aucune écriture générée pour {fichier.name}")
        return "ERREUR", "Aucune écriture générée"

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    df_final = pd.DataFrame(lignes_finales, columns=COLONNES_SORTIE)
    sortie   = DOSSIER_SORTIE / f"{fichier.stem}_ancv.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin-1")

    logger.info(f"[ANCV] OK {sortie.name} ({len(lignes_finales)} écritures)")
    return "OK", str(sortie)


__all__ = ["traiter_ancv"]
