import pandas as pd
from pathlib import Path


# ----------------------------
# UTILITAIRE INTERNE
# ----------------------------
def _get_engine(fichier: Path) -> str:
    """Retourne le bon engine selon l'extension du fichier"""
    return "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"


# ----------------------------
# AMEX CAISSE
# ----------------------------
def est_amex_caisse(fichier: Path) -> bool:
    try:
        fichier = Path(fichier)
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, header=None, engine=engine)
        # DLM est en colonne 6 (pas 14)
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
    """
    Détection uniquement par nom de fichier.
    Un fichier ANCV ne s'appellera jamais '*_ventes*'
    donc pas besoin d'appeler est_ancv() ici.
    """
    return (
        fichier.suffix.lower() == ".csv"
        and "_ventes" in fichier.stem.lower()
    )
