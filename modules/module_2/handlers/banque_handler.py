# handlers/module_2/banque_handler.py
"""
Module 2 : Chargement/parsing données bancaires pour justification
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from config import logger
from core.utils.montant import to_float
from core.utils.colonnes import CONTRATS_AMEX, RE_COMMANDE


# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotBanqueFileError(Exception):
    """Levée si aucune donnée bancaire exploitable n'est trouvée."""
    pass


# ==========================================================
# UTILITAIRES PRIVÉS
# ==========================================================

def _get_engine(fichier: Path) -> str:
    """Détecte le moteur pandas selon l'extension."""
    return "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"


def _nettoyer_commande(val) -> Optional[str]:
    """Extrait les 8 premiers chiffres du numéro de commande."""
    import re
    if pd.isna(val):
        return None
    chiffres = re.findall(r"\d", str(val))
    if len(chiffres) < 8:
        return None
    return "".join(chiffres[:8])


# ==========================================================
# DÉTECTION & CHARGEMENT
# ==========================================================

def est_banque(fichier: Path) -> bool:
    """
    Détecte un fichier banque via le numéro de contrat en colonne B.

    Contrats reconnus :
    - 7770571305 → AMEX
    - 831103222  → PLANET
    - 8430996    → CB
    """
    try:
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, header=None, engine=engine, dtype=str, nrows=100)
        col_b = df[1].astype(str).str.strip()
        return col_b.isin(CONTRATS_AMEX.keys()).any()
    except Exception:
        return False


def charger_banque(fichier: Path) -> pd.DataFrame:
    """
    Charge un fichier banque et retourne un DataFrame normalisé.

    Colonnes sortie :
    - num_commande : str (8 chiffres, colonne C sans le M initial)
    - type_flux    : str ('Débit' ou 'Crédit', colonne E)
    - montant      : float (colonne G)
    - source       : str ('AMEX', 'PLANET' ou 'CB')
    - date         : date (colonne A)

    Raises:
        NotBanqueFileError: Si aucune donnée exploitable
    """
    try:
        engine = _get_engine(fichier)
        df_raw = pd.read_excel(fichier, header=None, engine=engine, dtype=str)

        logger.info(f"Chargement Banque : {fichier.name} ({len(df_raw)} lignes)")

        # Identifier la source via colonne B (indice 1)
        col_b = df_raw[1].astype(str).str.strip()
        source = "INCONNU"
        for num, nom in CONTRATS_AMEX.items():
            if col_b.isin([num]).any():
                source = nom
                break

        logger.info(f"  Source détectée : {source}")

        # Extraction des colonnes
        # A=0 (date), C=2 (commande), E=4 (type), G=6 (montant)
        resultat = pd.DataFrame()

        resultat["date"] = pd.to_datetime(df_raw[0], errors="coerce")
        resultat["num_commande"] = (
            df_raw[2].astype(str).str.strip()
            .str.replace(r"^M", "", regex=True)  # enlève le M initial
            .str.extract(r"(\d{8})")[0]  # garde 8 chiffres
        )
        resultat["type_flux"] = df_raw[4].astype(str).str.strip()
        resultat["montant"] = pd.to_numeric(df_raw[6], errors="coerce")
        resultat["source"] = source

        # Filtrage
        resultat = resultat.dropna(subset=["num_commande", "montant"])
        resultat = resultat[resultat["num_commande"].str.match(r"^\d{8}$", na=False)]

        logger.info(f"✅ Banque chargée : {len(resultat)} transactions {source}")

        return resultat

    except Exception as e:
        logger.error(f"Erreur lors du chargement Banque : {e}")
        raise NotBanqueFileError(f"Erreur Banque {fichier.name} : {e}")


def traiter_banque(fichier: Path) -> Optional[pd.DataFrame]:
    """Point d'entrée pour le dispatcher."""
    try:
        df = charger_banque(fichier)
        return df
    except NotBanqueFileError as e:
        logger.error(f"❌ {e}")
        return None
