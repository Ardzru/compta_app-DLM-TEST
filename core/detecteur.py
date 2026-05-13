# core/detecteur.py

import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CONTRATS_BANQUE = {
    "7770571305": "AMEX",
    "831103222":  "PLANET",
    "8430996":    "CB",
}

def _get_engine(fichier: Path) -> str:
    """Détermine le moteur de lecture Excel."""
    if fichier.suffix.lower() == ".xls":
        return "xlrd"
    return "openpyxl"

# ----------------------------
# UTILITAIRE INTERNE
# ----------------------------
def _get_engine(fichier: Path) -> str:
    return "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"


# ----------------------------
# AMEX CAISSE
# ----------------------------
def est_amex_caisse(fichier: Path) -> bool:
    try:
        fichier = Path(fichier)
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, header=None, engine=engine)
        signatures = df[6].astype(str).str.strip().str.upper()
        return (signatures == "DLM").any()
    except:
        return False


# ----------------------------
# AMEX INTERNET
# ----------------------------
def est_amex_internet(fichier: Path) -> bool:
    try:
        fichier = Path(fichier)
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, header=None, engine=engine)
        signatures = df[14].astype(str).str.upper()
        return signatures.str.contains("SITE", na=False).any()
    except:
        return False

# ----------------------------
# PLANET  ← AVANT ALMA
# ----------------------------
def est_planet(fichier: Path) -> bool:
    if fichier.suffix.lower() != ".xlsx":
        return False
    try:
        fichier = Path(fichier)
        df = pd.read_excel(fichier, header=None, engine="openpyxl", nrows=10)

        for i in range(min(10, len(df))):
            headers = df.iloc[i].astype(str).str.strip().str.upper().tolist()
            # Planet a toujours ces colonnes spécifiques
            if "MID" in headers and "TERMINAL ID" in headers:
                logger.debug(f"[PLANET] ✅ {fichier.name} — ligne {i}")
                return True
            # Variante : Batch No. + Gross Amount EUR = signature Planet
            if "BATCH NO." in headers and "GROSS AMOUNT EUR" in headers:
                logger.debug(f"[PLANET] ✅ {fichier.name} — ligne {i} (signature Batch/Gross)")
                return True

        logger.debug(f"[PLANET] ❌ {fichier.name} — aucune signature trouvée")
        return False
    except Exception as e:
        logger.debug(f"[PLANET] ❌ {fichier.name} — exception: {e}")
        return False


# ----------------------------
# ALMA
# ----------------------------
def est_alma(fichier: Path) -> bool:
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False
    try:
        fichier = Path(fichier)
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, engine=engine)
    except:
        return False
    colonnes = [str(c).lower() for c in df.columns]
    mots_cles = ["alma", "commission", "frais", "tva", "installment", "payout"]
    return any(mot in col for col in colonnes for mot in mots_cles)


# ----------------------------
# ANCV
# ----------------------------
def est_ancv(fichier: Path) -> bool:
    if fichier.suffix.lower() != ".csv":
        return False
    try:
        for sep in ["\t", ";", ","]:
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(fichier, sep=sep, dtype=str, nrows=20,
                                     encoding=encoding)
                    df.columns = [c.strip() for c in df.columns]
                    if df.apply(lambda col: col.str.contains("VALIDATED", na=False)).any().any():
                        return True
                except Exception:
                    continue
        return False
    except Exception:
        return False


# ----------------------------
# TA
# ----------------------------
def est_ta(fichier: Path) -> bool:
    try:
        fichier = Path(fichier)
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, engine=engine)
        colonnes = [str(c).strip().upper() for c in df.columns]
        return (
            "VALEUR PROMPT" in colonnes
            and "TRANSACTION" in colonnes
            and "CAISSE" in colonnes
            and "MONTANT" in colonnes
        )
    except:
        return False


# ----------------------------
# AVOIRS
# ----------------------------
def est_avoirs(fichier: Path) -> bool:
    try:
        fichier = Path(fichier)
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, engine=engine)
        colonnes = [str(c).lower() for c in df.columns]
        return (
            "points" in colonnes
            and "commande liée" in colonnes
            and "nom statut" in colonnes
        )
    except:
        return False


# ----------------------------
# KIOSK PHOTO LUGE
# ----------------------------
def est_kiosk_photo(fichier: Path) -> bool:
    return (
        fichier.suffix.lower() == ".csv"
        and "_ventes" in fichier.stem.lower()
    )

# ----------------------------
# BANQUE INTERNET (AMEX/PLANET/CB)
# Détection : colonne B contient un numéro de contrat connu
# ----------------------------
def est_banque_internet(fichier: Path) -> bool:
    """
    Détecte un fichier banque internet via le numéro de contrat
    présent en colonne B (AMEX / PLANET / CB).
    Critère visuel : Image 1 (liste de transactions avec colonnes)
    """
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False

    try:
        engine = _get_engine(fichier)
        # Lecture des 200 premières lignes pour la performance
        df = pd.read_excel(fichier, header=None, engine=engine,
                          nrows=200, dtype=str)

        # Vérification minimale : au moins 2 colonnes
        if df.shape[1] < 2:
            return False

        # Colonnes visibles : [Date, Crédit, Journal, Libellé écriture, Débit, ...]
        # On vérifie que la colonne B (index 1) contient un numéro de contrat
        col_b = df[1].astype(str).str.strip()
        return col_b.isin(CONTRATS_BANQUE.keys()).any()

    except Exception as e:
        print(f"Erreur détection Banque {fichier.name}: {e}")
        return False

# ----------------------------
# ALPILINK
# Détection : Fichiers nommés "Data.xlsx", "Data(1).xlsx", etc.
# Critère visuel : Image 2 ou 3 (fichiers avec données clients/commandes)
# ----------------------------
def est_alpilink(fichier: Path) -> bool:
    """
    Détecte un fichier Alpilink via le nom du fichier.
    Critère visuel : Fichiers commençant par 'Data' (Image 2 ou 3)
    """
    return (
        fichier.suffix.lower() in [".xls", ".xlsx"]
        and fichier.stem.lower().startswith("data")
    )

# ----------------------------
# COMPTA INTERNET (SAGE)
# Détection : Fichiers avec colonnes "Libellé écriture" et "Journal"
# Critère visuel : Image 4 (fichier Sage avec colonnes spécifiques)
# ----------------------------
def est_compta_internet(fichier: Path) -> bool:
    try:
        fichier = Path(fichier)
        logger.info(f"🔍 Vérification fichier COMPTA: {fichier.name}")

        if fichier.suffix.lower() not in [".xls", ".xlsx"]:
            return False

        nom_fichier = fichier.name.lower()

        # ✅ AJOUT : exclure explicitement les fichiers Planet
        if nom_fichier.startswith("fr_") and "statement" in nom_fichier:
            logger.info(f"⛔ Exclu (Planet Statement): {fichier.name}")
            return False

        if "pmt internet" not in nom_fichier and "interr" not in nom_fichier:
            logger.warning(f"⚠️ Nom fichier ne correspond pas à COMPTA Internet: {fichier.name}")
            return False  # ← DÉCOMMENTER cette ligne !

        engine = "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"
        df = pd.read_excel(fichier, engine=engine, nrows=10)

        colonnes = [str(c).strip().lower().replace(" ", "") for c in df.columns]
        logger.info(f"🔤 Colonnes normalisées: {colonnes}")

        colonnes_requises = ["date", "libellé", "montant", "n°commande", "description", "amount", "transactionid"]
        colonnes_trouvees = sum(1 for col in colonnes if any(requis in col for requis in colonnes_requises))
        logger.info(f"🎯 Colonnes requises trouvées: {colonnes_trouvees}/{len(colonnes_requises)}")

        if colonnes_trouvees >= 3:
            logger.info(f"✅ Fichier COMPTA Internet détecté: {fichier.name}")
            return True

        return False

    except Exception as e:
        logger.error(f"💥 Erreur dans est_compta_internet({fichier}): {str(e)}")
        return False




