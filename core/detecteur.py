import pandas as pd
from pathlib import Path


# ----------------------------
# AMEX CAISSE
# ----------------------------
def est_amex_caisse(fichier):
    try:
        df = pd.read_excel(fichier, header=None, engine="xlrd")
        signatures = df[14].astype(str).str.upper()
        return (signatures == "DLM").any()
    except:
        return False


# ----------------------------
# AMEX INTERNET
# ----------------------------
def est_amex_internet(fichier):
    try:
        df = pd.read_excel(fichier, header=None, engine="xlrd")
        signatures = df[14].astype(str).str.upper()
        return signatures.str.contains("SITE", na=False).any()
    except:
        return False


# ----------------------------
# ALMA (NOUVEAU)
# ----------------------------
def est_alma(fichier: Path) -> bool:
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False

    try:
        engine = "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"
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
        df = pd.read_csv(fichier, sep=";", dtype=str)
    except:
        return False
    return df.apply(lambda col: col.str.contains("VALIDATED", na=False)).any().any()


# ----------------------------
# TA
# ----------------------------
def est_ta(fichier):
    try:
        df = pd.read_excel(fichier)
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
        df = pd.read_excel(fichier, engine="openpyxl")
    except:
        return False

    colonnes = [str(c).lower() for c in df.columns]

    return (
        "points" in colonnes
        and "commande liée" in colonnes
        and "nom statut" in colonnes
    )

# ----------------------------
# KIOSK PHOTO LUGE
# ----------------------------
def est_kiosk_photo(fichier: Path) -> bool:
    return (
        fichier.suffix.lower() == ".csv"
        and "_ventes" in fichier.stem.lower()
        and not est_ancv(fichier)
    )
