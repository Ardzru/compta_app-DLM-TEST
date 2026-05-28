"""
===============================================================================
core/detecteur.py
===============================================================================
Module de détection automatique des types de fichiers comptables.
Chaque fonction retourne True/False selon si le fichier correspond au type.

RÈGLE : Une fonction ne doit dépendre d'AUCUN module métier.
        Elle est générique et réutilisable.
===============================================================================
"""

import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES
# ============================================================================

CONTRATS_BANQUE = {
    "7770571305": "AMEX",
    "831103222":  "PLANET",
    "8430996":    "CB",
}

# ============================================================================
# UTILITAIRES INTERNES
# ============================================================================

def _get_engine(fichier: Path) -> str:
    """
    Détermine le moteur de lecture Excel selon l'extension.

    Args:
        fichier: Chemin du fichier

    Returns:
        "xlrd" pour .xls (ancien Excel)
        "openpyxl" pour .xlsx (nouveau Excel)
    """
    if not isinstance(fichier, Path):
        fichier = Path(fichier)

    if fichier.suffix.lower() == ".xls":
        return "xlrd"
    return "openpyxl"


def _charger_excel_safe(fichier: Path, nrows: int = 10, header=None):
    """
    Charge un fichier Excel de manière sûre.

    Args:
        fichier: Chemin du fichier
        nrows: Nombre de lignes à charger
        header: Ligne d'en-tête (None = pas d'en-tête)

    Returns:
        DataFrame ou None si erreur
    """
    try:
        engine = _get_engine(fichier)
        return pd.read_excel(
            fichier,
            header=header,
            engine=engine,
            nrows=nrows,
            dtype=str
        )
    except Exception as e:
        logger.debug(f"⚠️ Impossible de charger {fichier.name}: {e}")
        return None


def _normaliser_colonnes(df) -> list:
    """
    Normalise les noms de colonnes : lowercase, strip, pas d'espaces.

    Args:
        df: DataFrame pandas

    Returns:
        Liste des colonnes normalisées
    """
    if df is None or df.empty:
        return []
    return [str(c).strip().lower().replace(" ", "") for c in df.columns]


def _contient_colonne(colonnes: list, motifs: list) -> int:
    """
    Compte combien de motifs sont trouvés dans les colonnes.

    Args:
        colonnes: Liste des colonnes normalisées
        motifs: Liste des motifs à chercher

    Returns:
        Nombre de motifs trouvés
    """
    count = 0
    for col in colonnes:
        for motif in motifs:
            if motif in col:
                count += 1
                break
    return count

# ============================================================================
# DÉTECTEURS MÉTIER - MODULE 1 (CONVERSION)
# ============================================================================

def est_amex_caisse(fichier: Path) -> bool:
    """
    Détecte : AMEX CAISSE
    Critère : Colonne F (index 6) contient "DLM"
    """
    try:
        fichier = Path(fichier)
        df = _charger_excel_safe(fichier, nrows=50, header=None)

        if df is None or df.empty or df.shape[1] < 7:
            return False

        signatures = df[6].astype(str).str.strip().str.upper()
        return (signatures == "DLM").any()
    except Exception as e:
        logger.debug(f"est_amex_caisse({fichier.name}): {e}")
        return False


def est_amex_internet(fichier: Path) -> bool:
    """
    Détecte : AMEX INTERNET
    Critère : Colonne O (index 14) contient "SITE"
    """
    try:
        fichier = Path(fichier)
        df = _charger_excel_safe(fichier, nrows=50, header=None)

        if df is None or df.empty or df.shape[1] < 15:
            return False

        signatures = df[14].astype(str).str.upper()
        return signatures.str.contains("SITE", na=False).any()
    except Exception as e:
        logger.debug(f"est_amex_internet({fichier.name}): {e}")
        return False


def est_planet(fichier: Path) -> bool:
    """
    Détecte : PLANET
    Critère : Présence colonnes "MID" + "TERMINAL ID"
              OU "BATCH NO." + "GROSS AMOUNT EUR"
    """
    if fichier.suffix.lower() != ".xlsx":
        return False

    try:
        fichier = Path(fichier)
        df = _charger_excel_safe(fichier, nrows=10, header=None)

        if df is None or df.empty:
            return False

        # Chercher la ligne d'en-tête dans les 10 premières lignes
        for i in range(min(10, len(df))):
            headers = df.iloc[i].astype(str).str.strip().str.upper().tolist()

            # Signature 1 : MID + TERMINAL ID
            if "MID" in headers and "TERMINAL ID" in headers:
                logger.info(f"✅ PLANET détecté : {fichier.name} (ligne {i})")
                return True

            # Signature 2 : BATCH NO. + GROSS AMOUNT EUR
            if "BATCH NO." in headers and "GROSS AMOUNT EUR" in headers:
                logger.info(f"✅ PLANET détecté : {fichier.name} (Batch/Gross)")
                return True

        logger.debug(f"❌ PLANET non détecté : {fichier.name}")
        return False

    except Exception as e:
        logger.debug(f"est_planet({fichier.name}): {e}")
        return False


def est_alma(fichier: Path) -> bool:
    """
    Détecte : ALMA PAYMENTS
    Critère : Colonnes spécifiques Alma
      - "Identifiant paiement"
      - "Montant achat"
      - "Référence de commande"
      - "Créé (Heure Europe/Paris)"
    """
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False

    try:
        df = _charger_excel_safe(fichier, nrows=5, header=0)

        if df is None or df.empty:
            return False

        colonnes = _normaliser_colonnes(df)

        # Signatures ALMA spécifiques
        signatures_alma = [
            "identifiantpaiement",
            "montantachat",
            "referencede commande",
            "crééheure"
        ]

        count = _contient_colonne(colonnes, signatures_alma)

        if count >= 3:
            logger.info(f"✅ ALMA PAYMENTS détecté : {fichier.name}")
            return True

        logger.debug(f"⚠️ ALMA : {count}/3 colonnes trouvées")
        return False

    except Exception as e:
        logger.debug(f"est_alma({fichier.name}): {e}")
        return False


def est_ancv(fichier: Path) -> bool:
    """
    Détecte : ANCV
    Critère : Fichier CSV contenant "VALIDATED"
    """
    if fichier.suffix.lower() != ".csv":
        return False

    try:
        # Essayer différents séparateurs et encodages
        for sep in ["\t", ";", ","]:
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(
                        fichier,
                        sep=sep,
                        dtype=str,
                        nrows=20,
                        encoding=encoding
                    )

                    df.columns = [c.strip() for c in df.columns]

                    # Vérifier "VALIDATED" dans les données
                    if df.apply(lambda col: col.str.contains("VALIDATED", na=False)).any().any():
                        logger.info(f"✅ ANCV détecté : {fichier.name}")
                        return True

                except Exception:
                    continue

        return False

    except Exception as e:
        logger.debug(f"est_ancv({fichier.name}): {e}")
        return False


def est_ta(fichier: Path) -> bool:
    """
    Détecte : TA (Trésorier)
    Critère : Colonnes "VALEUR PROMPT", "TRANSACTION", "CAISSE", "MONTANT"
    """
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False

    try:
        df = _charger_excel_safe(fichier, nrows=10)

        if df is None or df.empty:
            return False

        colonnes = [str(c).strip().upper() for c in df.columns]

        criteres = [
            "VALEUR PROMPT" in colonnes,
            "TRANSACTION" in colonnes,
            "CAISSE" in colonnes,
            "MONTANT" in colonnes,
        ]

        if all(criteres):
            logger.info(f"✅ TA détecté : {fichier.name}")
            return True

        return False

    except Exception as e:
        logger.debug(f"est_ta({fichier.name}): {e}")
        return False


def est_avoirs(fichier: Path) -> bool:
    """
    Détecte : AVOIRS
    Critère : Colonnes "POINTS", "COMMANDE LIÉE", "NOM STATUT"
    """
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False

    try:
        df = _charger_excel_safe(fichier, nrows=10)

        if df is None or df.empty:
            return False

        colonnes = [str(c).lower() for c in df.columns]

        criteres = [
            "points" in colonnes,
            "commande liée" in colonnes,
            "nom statut" in colonnes,
        ]

        if all(criteres):
            logger.info(f"✅ AVOIRS détecté : {fichier.name}")
            return True

        return False

    except Exception as e:
        logger.debug(f"est_avoirs({fichier.name}): {e}")
        return False


def est_kiosk_photo(fichier: Path) -> bool:
    """
    Détecte : KIOSK PHOTO
    Critère : Fichier CSV avec "_ventes" dans le nom
    """
    try:
        return (
            fichier.suffix.lower() == ".csv"
            and "_ventes" in fichier.stem.lower()
        )
    except Exception as e:
        logger.debug(f"est_kiosk_photo({fichier.name}): {e}")
        return False

# ============================================================================
# DÉTECTEURS MÉTIER - MODULE 2 (JUSTIFICATION)
# ============================================================================

def est_banque_internet(fichier: Path) -> bool:
    """
    Détecte : BANQUE INTERNET (AMEX / PLANET / CB)
    Critère : Colonne B (index 1) contient un numéro de contrat connu
    """
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False

    try:
        df = _charger_excel_safe(fichier, nrows=200, header=None)

        if df is None or df.empty or df.shape[1] < 2:
            return False

        # Vérifier colonne B (index 1) pour numéros de contrat
        col_b = df[1].astype(str).str.strip()

        if col_b.isin(CONTRATS_BANQUE.keys()).any():
            logger.info(f"✅ BANQUE INTERNET détecté : {fichier.name}")
            return True

        return False

    except Exception as e:
        logger.debug(f"est_banque_internet({fichier.name}): {e}")
        return False


def est_alpilink(fichier: Path) -> bool:
    """
    Détecte : ALPILINK
    Critère : Fichier nommé "Data.xlsx", "Data(1).xlsx", etc.
    """
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False

    try:
        nom_clean = fichier.stem.lower()

        if nom_clean.startswith("data"):
            logger.info(f"✅ ALPILINK détecté : {fichier.name}")
            return True

        return False

    except Exception as e:
        logger.debug(f"est_alpilink({fichier.name}): {e}")
        return False


def est_compta_internet(fichier: Path) -> bool:
    """
    Détecte : COMPTA INTERNET (Sage)
    Critère :
      1. Nom contient "PMT INTERNET" ou "INTERR"
      2. EXCLURE les fichiers Planet (fr_*_statement)
      3. Colonnes contiennent "date", "libellé", "montant" (au moins 3)
    """
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False

    try:
        nom_fichier = fichier.name.lower()

        # ✅ EXCLUSION : fichiers Planet
        if nom_fichier.startswith("fr_") and "statement" in nom_fichier:
            logger.debug(f"⛔ Exclu (Planet Statement): {fichier.name}")
            return False

        # ✅ INCLUSION : patterns COMPTA
        if "pmt internet" not in nom_fichier and "interr" not in nom_fichier:
            logger.debug(f"⚠️ Nom ne correspond pas (COMPTA): {fichier.name}")
            return False

        # Charger et analyser colonnes
        df = _charger_excel_safe(fichier, nrows=10)

        if df is None or df.empty:
            return False

        colonnes = _normaliser_colonnes(df)
        motifs_requis = [
            "date",
            "libellé",
            "montant",
            "n°commande",
            "description",
            "amount",
            "transactionid"
        ]

        count = _contient_colonne(colonnes, motifs_requis)

        if count >= 3:
            logger.info(f"✅ COMPTA INTERNET détecté : {fichier.name}")
            return True

        logger.debug(f"❌ COMPTA INTERNET : colonnes insuffisantes ({count}/3)")
        return False

    except Exception as e:
        logger.error(f"❌ est_compta_internet({fichier.name}): {e}")
        return False

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Utilitaires
    '_get_engine',
    '_charger_excel_safe',
    '_normaliser_colonnes',
    '_contient_colonne',
    # Module 1
    'est_amex_caisse',
    'est_amex_internet',
    'est_alma',
    'est_ancv',
    'est_avoirs',
    'est_kiosk_photo',
    'est_ta',
    'est_planet',
    # Module 2
    'est_banque_internet',
    'est_alpilink',
    'est_compta_internet',
]
