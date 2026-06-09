# modules/module_2/handlers/banque_handler.py
"""
Module 2 - Handler BANQUE
Chargement et extraction des commandes depuis fichiers de remises bancaires.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from config import logger
from core.utils.commandes import normaliser_cmd


# ==========================================================
# EXCEPTION METIER
# ==========================================================

class NotBanqueFileError(Exception):
    """Levee si aucune remise bancaire exploitable n'est trouvee."""
    pass


# ==========================================================
# DETECTION COLONNES
# ==========================================================

def _trouver_colonnes(df: pd.DataFrame) -> dict:
    """
    Détecte les colonnes DATE, COMMANDE, LIBELLE, MONTANT
    dans un dataframe de remise bancaire.

    Retourne dict avec clés: date_idx, commande_idx, libelle_idx, montant_idx
    (et _col pour le nom de colonne)
    """
    result = {}
    cols_lower = [str(c).lower() for c in df.columns]

    # Cherche DATE
    date_idx = None
    for i, col in enumerate(cols_lower):
        if any(kw in col for kw in ['date du paiement', 'date paiement', 'date', 'dateheure']):
            date_idx = i
            break
    if date_idx is None:
        date_idx = 0

    result['date_idx'] = date_idx
    result['date_col'] = df.columns[date_idx] if date_idx < len(df.columns) else "INCONNU"

    # Cherche COMMANDE
    commande_idx = None
    for i, col in enumerate(cols_lower):
        if any(kw in col for kw in ['commande', 'numéro de commande', 'n° commande', 'order id']):
            commande_idx = i
            break
    if commande_idx is None:
        commande_idx = 3

    result['commande_idx'] = commande_idx
    result['commande_col'] = df.columns[commande_idx] if commande_idx < len(df.columns) else "INCONNU"

    # Cherche LIBELLE (contrat ou description)
    libelle_idx = None
    for i, col in enumerate(cols_lower):
        if any(kw in col for kw in ['contrat courant', 'contrat', 'description', 'libelle', 'libel']):
            libelle_idx = i
            break
    if libelle_idx is None:
        libelle_idx = 1

    result['libelle_idx'] = libelle_idx
    result['libelle_col'] = df.columns[libelle_idx] if libelle_idx < len(df.columns) else "INCONNU"

    # ✅ Cherche MONTANT - PRIORITÉ STRICTE
    montant_idx = None
    for i, col in enumerate(cols_lower):
        if "montant du paiement" in col:  # ← PRIORITÉ 1
            montant_idx = i
            break
    if montant_idx is None:
        for i, col in enumerate(cols_lower):
            if "montant" in col and "remboursé" not in col and "remise" not in col:  # ← PRIORITÉ 2
                montant_idx = i
                break
    if montant_idx is None:
        montant_idx = 7  # Fallback colonne H (index 7)

    result['montant_idx'] = montant_idx
    result['montant_col'] = df.columns[montant_idx] if montant_idx < len(df.columns) else "INCONNU"

    logger.debug(
        f"[BanqueHandler] Colonnes détectées : "
        f"date={result['date_col']} (idx {result['date_idx']}), "
        f"commande={result['commande_col']} (idx {result['commande_idx']}), "
        f"libelle={result['libelle_col']} (idx {result['libelle_idx']}), "
        f"montant={result['montant_col']} (idx {result['montant_idx']})"
    )

    return result


# ==========================================================
# CHARGEMENT
# ==========================================================

def _get_engine(fichier: Path) -> str:
    """Détecte le bon moteur openpyxl/xlrd pour le fichier."""
    if fichier.suffix.lower() == ".xlsx":
        return "openpyxl"
    return "xlrd"


def charger_banque(fichier: Path) -> pd.DataFrame:
    """Charge un fichier de remises bancaires avec montants."""
    try:
        if fichier.suffix.lower() == ".csv":
            df = pd.read_csv(fichier, sep=";", dtype=str, encoding="utf-8")
        else:
            df = pd.read_excel(fichier, engine=_get_engine(fichier), dtype=str)

        logger.debug(f"[BanqueHandler] Colonnes brutes : {df.columns.tolist()}")
        logger.debug(f"[BanqueHandler] Shape : {df.shape}")

        # ✅ STRUCTURE STANDARD : A=date, B=contrat, C=commerçant, D=commande, H=montant
        # Mais utilise detection robuste
        cols_info = _trouver_colonnes(df)

        resultat = pd.DataFrame()

        # DATE
        resultat["date"] = pd.to_datetime(
            df.iloc[:, cols_info['date_idx']], errors="coerce"
        ).dt.strftime("%d/%m/%Y")

        # COMMANDE
        resultat["commande"] = df.iloc[:, cols_info['commande_idx']].fillna("").astype(str).str.strip()

        # LIBELLE (contrat ou description)
        resultat["libelle"] = df.iloc[:, cols_info['libelle_idx']].fillna("").astype(str).str.strip()

        # MONTANT
        resultat["montant"] = pd.to_numeric(
            df.iloc[:, cols_info['montant_idx']].fillna(0).astype(str).str.replace(",", "."),
            errors="coerce"
        ).fillna(0)

        # Filtre les lignes sans commande
        resultat = resultat[resultat["commande"].notna() & (resultat["commande"] != "")]

        if resultat.empty:
            raise NotBanqueFileError(f"Aucune commande exploitable dans {fichier.name}")

        logger.info(
            f"[BanqueHandler] {len(resultat)} lignes | "
            f"Commandes non-vides : {len(resultat)}/{len(df)} | "
            f"Exemples : {resultat['commande'].head(3).tolist()}"
        )

        return resultat

    except Exception as e:
        logger.error(f"[BanqueHandler] Erreur chargement {fichier.name}: {e}", exc_info=True)
        raise NotBanqueFileError(str(e))


# ==========================================================
# EXTRACTION COMMANDES
# ==========================================================

def extraire_commandes(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """
    Extrait les commandes valides du dataframe BANQUE.

    Retourne:
        (list des commandes valides, list des commandes rejetées)

    ✅ Utilise normaliser_cmd() pour validation uniforme
    """
    resultat = []
    resultat_rejetees = []
    error_count = 0
    ligne_count = len(df)

    for idx, row in df.iterrows():
        try:
            # ✅ UTILISE normaliser_cmd()
            cmd_raw = str(row.get("commande", "")).strip()
            cmd = normaliser_cmd(cmd_raw)

            if not cmd:  # ✅ Rejette les commandes invalides
                logger.debug(f"[BanqueHandler] Ligne {idx} : cmd invalide '{cmd_raw}', ignorée")
                resultat_rejetees.append({
                    "commande_raw": cmd_raw,
                    "raison": "commande invalide",
                })
                continue

            montant = float(row.get("montant", 0))
            date = str(row.get("date", ""))

            if montant == 0.0:
                logger.warning(f"[BanqueHandler] Ligne {idx} : montant = 0, ignorée")
                resultat_rejetees.append({
                    "commande": cmd,
                    "raison": "montant zéro",
                })
                continue

            resultat.append({
                "commande": cmd,  # ✅ Maintenant normalisée
                "montant": montant,
                "date": date,
                "source_banque": "remise_bancaire",
            })

        except Exception as e:
            error_count += 1
            logger.error(f"[BanqueHandler] Erreur ligne {idx}: {e}", exc_info=True)
            resultat_rejetees.append({
                "commande_raw": str(row.get("commande", "?")),
                "raison": str(e),
            })

    logger.info(
        f"[BanqueHandler] Extraction : {len(resultat)} commandes valides | "
        f"{len(resultat_rejetees)}/{ligne_count} rejetées"
    )

    return resultat, resultat_rejetees  # ✅ RETOURNE TUPLE


# ==========================================================
# POINT D'ENTREE
# ==========================================================

def traiter_banque(fichier: Path) -> Optional[pd.DataFrame]:
    """Point d'entree pour le dispatcher."""
    logger.info(f"[MODULE2][START] traiter_banque appele : {fichier.name}")
    try:
        df = charger_banque(fichier)
        logger.info(f"[MODULE2][OK] traiter_banque : {len(df)} lignes retournees")
        return df
    except NotBanqueFileError as e:
        logger.error(f"[MODULE2][FAIL] ❌ {e}")
        return None


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [
    "charger_banque",
    "extraire_commandes",
    "traiter_banque",
    "NotBanqueFileError",
]
