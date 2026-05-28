# handlers/module_2/alpilink_handler.py
"""
Module 2 : Chargement/parsing données Alpilink pour justification
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Tuple
from config import logger
from core.utils.montant import to_float
from core.utils.colonnes import ALPILINK_STATUTS_VALIDES, PRO_PARTENAIRES

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotAlpilinkFileError(Exception):
    """Levée si aucune donnée Alpilink exploitable n'est trouvée."""
    pass

# ==========================================================
# UTILITAIRES PRIVÉS
# ==========================================================

def _get_engine(fichier: Path) -> str:
    """Détecte le moteur pandas selon l'extension."""
    return "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"


def _get_pro_name(portail_id) -> Optional[str]:
    """Récupère le nom du partenaire PRO via le numéro de portail."""
    try:
        num = int(float(portail_id)) if portail_id else None
        return PRO_PARTENAIRES.get(num) if num else None
    except (ValueError, TypeError):
        return None

# ==========================================================
# DÉTECTION & CHARGEMENT
# ==========================================================

def est_alpilink(fichier: Path) -> bool:
    """Détecte un fichier Alpilink : nom commence par 'data'"""
    return fichier.stem.lower().startswith("data")


def charger_alpilink(fichier: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Charge un fichier Alpilink et retourne deux DataFrames :

    1. df_normal  : commandes Alpilink classiques agrégées par num_commande
       Colonnes : num_commande | montant_total | statut | est_pro | nom_partenaire

    2. df_buyclub : commandes BuyClub (présence = détection OK)
       Colonnes : num_commande

    Raises:
        NotAlpilinkFileError: Si aucune donnée exploitable
    """
    try:
        engine = _get_engine(fichier)
        df_raw = pd.read_excel(fichier, header=0, engine=engine, dtype=str)

        logger.info(f"Chargement Alpilink : {fichier.name} ({len(df_raw)} lignes)")

        # Accès par lettre de colonne
        def col(lettre):
            idx = ord(lettre.upper()) - ord('A')
            return df_raw.iloc[:, idx] if idx < len(df_raw.columns) else pd.Series(dtype=str)

        col_a = col("A").astype(str).str.strip()
        col_c = col("C").astype(str).str.strip()
        col_r = col("R").astype(str).str.strip()
        col_s = col("S").astype(str).str.strip()
        col_y = col("Y").astype(str).str.strip()
        col_z = pd.to_numeric(col("Z"), errors="coerce")

        df_work = pd.DataFrame({
            "col_a":    col_a,
            "col_c":    col_c,
            "col_r":    col_r,
            "col_s":    col_s,
            "col_y":    col_y,
            "montant":  col_z,
        })

        # ----------------------------------------------------------
        # Séparation BuyClub
        # ----------------------------------------------------------
        mask_buyclub = df_work["col_c"].str.upper().str.contains("SC9972:BUY", na=False)
        df_buyclub = df_work[mask_buyclub][["col_r"]].rename(columns={"col_r": "num_commande"})
        df_buyclub = df_buyclub.dropna(subset=["num_commande"])

        logger.info(f"  BuyClub détecté : {len(df_buyclub)} lignes")

        # ----------------------------------------------------------
        # Alpilink classique — filtrer statuts valides
        # ----------------------------------------------------------
        df_normal = df_work[~mask_buyclub].copy()
        df_normal = df_normal[df_normal["col_y"].isin(ALPILINK_STATUTS_VALIDES)]

        logger.info(f"  Alpilink classique (statut valide) : {len(df_normal)} lignes")

        # Numéro de commande : S si S != "0", sinon R
        df_normal["num_commande"] = df_normal.apply(
            lambda row: row["col_s"] if row["col_s"] != "0" else row["col_r"],
            axis=1
        )
        df_normal = df_normal.dropna(subset=["num_commande", "montant"])

        logger.info(f"  Après nettoyage : {len(df_normal)} lignes")

        # ----------------------------------------------------------
        # Agrégation montants par numéro de commande
        # ----------------------------------------------------------
        df_agg = (
            df_normal.groupby("num_commande", as_index=False)
            .agg({
                "montant":    "sum",
                "col_y":      "first",
                "col_a":      "first",
            })
            .rename(columns={
                "montant": "montant_total",
                "col_y":   "statut",
                "col_a":   "portail_id",
            })
        )

        # ----------------------------------------------------------
        # Détection PRO via colonne A (numéro portail)
        # ----------------------------------------------------------
        df_agg["nom_partenaire"] = df_agg["portail_id"].apply(_get_pro_name)
        df_agg["est_pro"] = df_agg["nom_partenaire"].notna()

        logger.info(
            f"✅ Alpilink chargé : {len(df_agg)} commandes "
            f"({df_agg['est_pro'].sum()} PRO)"
        )

        return df_agg, df_buyclub

    except Exception as e:
        logger.error(f"Erreur lors du chargement Alpilink : {e}")
        raise NotAlpilinkFileError(f"Erreur Alpilink {fichier.name} : {e}")


def traiter_alpilink(fichier: Path) -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
    """Point d'entrée pour le dispatcher."""
    try:
        df_normal, df_buyclub = charger_alpilink(fichier)
        return df_normal, df_buyclub
    except NotAlpilinkFileError as e:
        logger.error(f"❌ {e}")
        return None, None
