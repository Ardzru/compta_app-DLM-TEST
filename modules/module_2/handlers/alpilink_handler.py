"""
Module 2 - Handler ALPILINK
Chargement et extraction des commandes depuis ALPILINK.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from config import logger
from core.utils.commandes import normaliser_cmd

# ==========================================================
# EXCEPTION METIER
# ==========================================================

class NotAlpilinkFileError(Exception):
    """Levee si aucune donnee ALPILINK exploitable n'est trouvee."""
    pass

# ==========================================================
# DETECTION COLONNES
# ==========================================================

def _trouver_colonnes(df: pd.DataFrame) -> dict:
    """
    Détecte les colonnes ID_COMMANDE, MONTANT, TYPE dans ALPILINK.
    """
    result = {}
    cols_lower = [str(c).lower() for c in df.columns]

    # ID COMMANDE
    cmd_idx = None
    for i, col in enumerate(cols_lower):
        if any(kw in col for kw in ['id commande', 'commande', 'order id']):
            cmd_idx = i
            break
    if cmd_idx is None:
        cmd_idx = 17  # Colonne par défaut ALPILINK

    result['commande_idx'] = cmd_idx
    result['commande_col'] = df.columns[cmd_idx] if cmd_idx < len(df.columns) else "INCONNU"

    # MONTANT
    montant_idx = None
    for i, col in enumerate(cols_lower):
        if any(kw in col for kw in ['prix total', 'montant', 'amount']):
            montant_idx = i
            break
    if montant_idx is None:
        montant_idx = 24  # Colonne par défaut ALPILINK

    result['montant_idx'] = montant_idx
    result['montant_col'] = df.columns[montant_idx] if montant_idx < len(df.columns) else "INCONNU"

    # TYPE (optionnel)
    type_idx = None
    for i, col in enumerate(cols_lower):
        if "type" in col:
            type_idx = i
            break

    result['type_idx'] = type_idx
    result['type_col'] = df.columns[type_idx] if type_idx and type_idx < len(df.columns) else None

    logger.debug(
        f"[AlpilinkHandler] Colonnes détectées : "
        f"commande={result['commande_col']}, "
        f"montant={result['montant_col']}, "
        f"type={result['type_col']}"
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

def charger_alpilink(fichier: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Charge un fichier ALPILINK et sépare NORMAL vs BUYCLUB.

    Retourne:
        (df_normal, df_buyclub)
    """
    try:
        if fichier.suffix.lower() == ".csv":
            df = pd.read_csv(fichier, sep=";", dtype=str, encoding="utf-8")
        else:
            df = pd.read_excel(fichier, engine=_get_engine(fichier), dtype=str)

        logger.info(f"[AlpilinkHandler] Colonnes : {df.columns.tolist()}")
        logger.debug(f"[AlpilinkHandler] Shape : {df.shape}")

        # Sépare par Type si la colonne existe
        cols_lower = [str(c).lower() for c in df.columns]
        type_idx = None
        for i, col in enumerate(cols_lower):
            if "type" in col:
                type_idx = i
                break

        if type_idx is not None:
            df_normal = df[df.iloc[:, type_idx].astype(str).str.upper() == "CLASSIQUE"]
            df_buyclub = df[df.iloc[:, type_idx].astype(str).str.upper() == "BUYCLUB"]
            logger.debug(f"[AlpilinkHandler] Séparation : {len(df_normal)} Classique, {len(df_buyclub)} BuyClub")
        else:
            logger.warning("[AlpilinkHandler] Colonne 'Type' absente, traitement unifié")
            df_normal = df
            df_buyclub = pd.DataFrame()

        return df_normal, df_buyclub

    except Exception as e:
        logger.error(f"[AlpilinkHandler] Erreur chargement {fichier.name}: {e}", exc_info=True)
        raise NotAlpilinkFileError(str(e))

# ==========================================================
# EXTRACTION COMMANDES
# ==========================================================

def extraire_commandes_alpilink(df_normal: pd.DataFrame, df_buyclub: pd.DataFrame) -> List[Dict]:
    """
    Extrait les commandes des dataframes ALPILINK.

    ✅ Utilise normaliser_cmd() pour validation uniforme
    """
    resultat = []
    error_count = 0

    cols_info = _trouver_colonnes(df_normal)

    # Traite CLASSIQUE
    for idx, row in df_normal.iterrows():
        try:
            cmd_raw = str(row.iloc[cols_info['commande_idx']]).strip()
            cmd = normaliser_cmd(cmd_raw)  # ✅ NORMALISATION

            if not cmd:
                continue

            montant = float(str(row.iloc[cols_info['montant_idx']]).replace(",", ".").strip() or 0)

            resultat.append({
                "commande": cmd,  # ✅ Normalisée
                "montant": montant,
                "type": "Classique",
                "source_alpilink": "normal",
            })

        except Exception as e:
            error_count += 1
            logger.debug(f"[AlpilinkHandler] Erreur ligne NORMAL {idx}: {e}")

    # Traite BUYCLUB
    if not df_buyclub.empty:
        for idx, row in df_buyclub.iterrows():
            try:
                cmd_raw = str(row.iloc[cols_info['commande_idx']]).strip()
                cmd = normaliser_cmd(cmd_raw)  # ✅ NORMALISATION

                if not cmd:
                    continue

                montant = float(str(row.iloc[cols_info['montant_idx']]).replace(",", ".").strip() or 0)

                resultat.append({
                    "commande": cmd,  # ✅ Normalisée
                    "montant": montant,
                    "type": "BuyClub",
                    "source_alpilink": "buyclub",
                })

            except Exception as e:
                error_count += 1
                logger.debug(f"[AlpilinkHandler] Erreur ligne BUYCLUB {idx}: {e}")

    logger.info(
        f"[AlpilinkHandler] Extraction : {len(resultat)} commandes | {error_count} erreurs"
    )

    return resultat

# ==========================================================
# POINT D'ENTREE
# ==========================================================

def traiter_alpilink(fichier: Path) -> Optional[List[Dict]]:
    """Point d'entrée pour le dispatcher."""
    logger.info(f"[MODULE2][START] traiter_alpilink appele : {fichier.name}")
    try:
        df_normal, df_buyclub = charger_alpilink(fichier)
        result = extraire_commandes_alpilink(df_normal, df_buyclub)
        logger.info(f"[MODULE2][OK] traiter_alpilink : {len(result)} commandes retournees")
        return result
    except NotAlpilinkFileError as e:
        logger.error(f"[MODULE2][FAIL] ❌ {e}")
        return None

# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [
    "NotAlpilinkFileError",
    "charger_alpilink",
    "extraire_commandes_alpilink",
    "traiter_alpilink",
]
