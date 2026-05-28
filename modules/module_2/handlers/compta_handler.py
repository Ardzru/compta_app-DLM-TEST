# handlers/module_2/compta_handler.py
"""
Module 2 : Chargement/parsing données comptables (Sage) pour justification
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from config import logger
from core.utils.montant import to_float
from core.utils.colonnes import (
    COMPTA_COLONNES, COMPTA_JOURNAUX_VE, COMPTA_JOURNAUX_ARGENT,
    PRO_PARTENAIRES, RE_COMMANDE,
)

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotComptaFileError(Exception):
    """Levée si aucune donnée compta exploitable n'est trouvée."""
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

def est_compta(fichier: Path) -> bool:
    """Détecte un fichier compta via la colonne 'Libellé écriture'"""
    try:
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, engine=engine, nrows=5)
        return "Libellé écriture" in df.columns
    except Exception:
        return False


def charger_compta(fichier: Path) -> pd.DataFrame:
    """
    Charge le fichier compta Sage et retourne un DataFrame normalisé.

    Colonnes sortie :
    - num_commande  : str (extrait de 'Libellé écriture')
    - date          : datetime
    - montant_signe : float
    - debit         : float
    - credit        : float
    - journal       : str
    - type_ecriture : str ('VE', 'ARGENT_RECU' ou 'AUTRE')
    - est_pro       : bool
    - nom_partenaire: str ou None

    Raises:
        NotComptaFileError: Si aucune donnée exploitable
    """
    try:
        engine = _get_engine(fichier)
        df_raw = pd.read_excel(fichier, engine=engine, dtype=str)

        logger.info(f"Chargement Compta : {fichier.name} ({len(df_raw)} lignes)")

        # Nettoyage colonnes
        df_raw.columns = [c.strip() for c in df_raw.columns]

        # Vérification colonnes requises
        requises = list(COMPTA_COLONNES.values())
        manquantes = [c for c in requises if c not in df_raw.columns]
        if manquantes:
            raise NotComptaFileError(f"Colonnes manquantes : {manquantes}")

        resultat = pd.DataFrame()

        resultat["date"]          = pd.to_datetime(df_raw.get("Date", pd.Series()), errors="coerce")
        resultat["num_commande"]  = df_raw.get("Libellé écriture", pd.Series()).astype(str).str.strip()
        resultat["montant_signe"] = pd.to_numeric(df_raw.get("Montant signé", pd.Series()), errors="coerce")
        resultat["debit"]         = pd.to_numeric(df_raw.get("Débit", pd.Series()), errors="coerce")
        resultat["credit"]        = pd.to_numeric(df_raw.get("Crédit", pd.Series()), errors="coerce")
        resultat["journal"]       = df_raw.get("Journal", pd.Series()).astype(str).str.strip().str.upper()
        resultat["num_piece"]     = df_raw.get("N° pièce", pd.Series()).astype(str).str.strip()

        # Type d'écriture
        def type_ecriture(j):
            if j in COMPTA_JOURNAUX_VE:
                return "VE"
            elif j in COMPTA_JOURNAUX_ARGENT:
                return "ARGENT_RECU"
            return "AUTRE"

        resultat["type_ecriture"] = resultat["journal"].apply(type_ecriture)

        # Détection PRO via colonne A (première colonne)
        col_a = df_raw.iloc[:, 0].astype(str).str.strip()
        resultat["nom_partenaire"] = col_a.apply(_get_pro_name)
        resultat["est_pro"]        = resultat["nom_partenaire"].notna()

        # Filtrer uniquement les num_commande à 8 chiffres
        resultat = resultat[resultat["num_commande"].str.match(r"^\d{8}$", na=False)]
        resultat = resultat.dropna(subset=["montant_signe"])

        logger.info(
            f"✅ Compta chargée : {len(resultat)} lignes "
            f"| VE: {(resultat['type_ecriture'] == 'VE').sum()} "
            f"| PRO: {resultat['est_pro'].sum()}"
        )

        return resultat

    except Exception as e:
        logger.error(f"Erreur lors du chargement Compta : {e}")
        raise NotComptaFileError(f"Erreur Compta {fichier.name} : {e}")


def traiter_compta(fichier: Path) -> Optional[pd.DataFrame]:
    """Point d'entrée pour le dispatcher."""
    try:
        df = charger_compta(fichier)
        return df
    except NotComptaFileError as e:
        logger.error(f"❌ {e}")
        return None
