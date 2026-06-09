# core/detecteur.py

import pandas as pd
from pathlib import Path
from typing import Literal
import csv
import logging

logger = logging.getLogger(__name__)

CONTRATS_BANQUE = {
    "7770571305": "AMEX",
    "831103222":  "PLANET",
    "8430996":    "CB",
}

ANCV_BANQUE_CONVENTION = "899394"

# ============================================================================
# UTILITAIRES INTERNES
# ============================================================================

def _get_engine(fichier: Path) -> Literal["xlrd", "openpyxl"]:
    if fichier.suffix.lower() == ".xls":
        return "xlrd"
    return "openpyxl"

# ============================================================================
# DETECTEURS MODULE 1
# ============================================================================

def est_ancv_banque(fichier: Path) -> bool:
    """
    Détecte un relevé ANCV Connect (financier banque).
    Critères :
      - Extension .csv
      - Ligne 0 contient "RELEVE DE COMPTE"
      - Ligne 3 contient la convention 899394
    """
    fichier = Path(fichier)
    if fichier.suffix.lower() != ".csv":
        return False
    try:
        with open(fichier, encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=";")
            rows = []
            for i, row in enumerate(reader):
                rows.append(row)
                if i >= 4:
                    break

        if not rows or "RELEVE DE COMPTE" not in ";".join(rows[0]).upper():
            return False

        if len(rows) < 4:
            return False

        if ANCV_BANQUE_CONVENTION not in ";".join(rows[3]):
            return False

        logger.debug(f"[DETECTEUR] ANCV BANQUE détecté : {fichier.name}")
        return True

    except Exception as e:
        logger.debug(f"est_ancv_banque({fichier.name}) : {e}")
        return False


def est_amex_caisse(fichier: Path) -> bool:
    try:
        fichier = Path(fichier)
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, header=None, engine=engine)
        signatures = df[6].astype(str).str.strip().str.upper()
        return (signatures == "DLM").any()
    except:
        return False

def est_amex_internet(fichier: Path) -> bool:
    try:
        fichier = Path(fichier)
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, header=None, engine=engine)
        if df.shape[1] <= 14:
            return False
        signatures = df[14].astype(str).str.upper()
        return signatures.str.contains("SITE", na=False).any()
    except:
        return False

def _lire_valeurs_planet(fichier: Path) -> pd.DataFrame | None:
    if fichier.suffix.lower() != ".xlsx":
        return None
    try:
        return pd.read_excel(fichier, header=None, engine="openpyxl", dtype=str)
    except Exception as e:
        logger.debug(f"_lire_valeurs_planet({fichier.name}) : {e}")
        return None

def _est_fichier_planet(fichier: Path) -> bool:
    if fichier.suffix.lower() != ".xlsx":
        return False
    try:
        df = pd.read_excel(
            fichier, header=None, engine="openpyxl", nrows=10, dtype=str
        )
        for i in range(min(10, len(df))):
            headers = df.iloc[i].astype(str).str.strip().str.upper().tolist()
            if "MID" in headers and "TERMINAL ID" in headers:
                return True
            if "BATCH NO." in headers and "GROSS AMOUNT EUR" in headers:
                return True
        return False
    except Exception as e:
        logger.debug(f"_est_fichier_planet({fichier.name}) : {e}")
        return False

def est_planet_caisse(fichier: Path) -> bool:
    if not _est_fichier_planet(fichier):
        return False
    try:
        df = _lire_valeurs_planet(fichier)
        if df is None or df.shape[1] <= 10:
            return False
        col_c = df[2].astype(str).str.strip()
        col_j = df[9].astype(str).str.strip().str.upper()
        col_k = df[10].astype(str).str.strip().str.upper()
        a_dcc     = col_c.str.upper().eq("DCC").any()
        a_instore = col_j.str.contains("INSTORE", na=False).any()
        a_pos     = col_k.str.contains("POS", na=False).any()
        result = a_dcc and a_instore and a_pos
        if result:
            logger.info(f"PLANET CAISSE détecté : {fichier.name}")
        return result
    except Exception as e:
        logger.debug(f"est_planet_caisse({fichier.name}) : {e}")
        return False

def est_planet_internet(fichier: Path) -> bool:
    if not _est_fichier_planet(fichier):
        return False
    try:
        df = _lire_valeurs_planet(fichier)
        if df is None or df.shape[1] <= 10:
            return False
        col_c = df[2].astype(str).str.strip().str.upper()
        col_j = df[9].astype(str).str.strip().str.upper()
        col_k = df[10].astype(str).str.strip().str.upper()
        a_dcc_local = col_c.str.contains("DCC/LOCAL", na=False).any()
        a_ecommerce = col_j.str.contains("ECOMMERCE", na=False).any()
        a_payzen    = col_k.str.contains("PAYZEN", na=False).any()
        result = a_dcc_local and a_ecommerce and a_payzen
        if result:
            logger.info(f"PLANET INTERNET détecté : {fichier.name}")
        return result
    except Exception as e:
        logger.debug(f"est_planet_internet({fichier.name}) : {e}")
        return False

def est_planet(fichier: Path) -> bool:
    return est_planet_caisse(fichier) or est_planet_internet(fichier)

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

def est_ancv(fichier: Path) -> bool:
    """
    Détecte ANCV classique (VALIDATED).
    ⚠️ Ne doit PAS matcher les relevés ANCV Banque (convention 899394).
    """
    if fichier.suffix.lower() != ".csv":
        return False
    # Exclure les relevés ANCV Banque
    if est_ancv_banque(fichier):
        return False
    try:
        for sep in ["\t", ";", ","]:
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(
                        fichier, sep=sep, dtype=str, nrows=20,
                        encoding=encoding
                    )
                    df.columns = [c.strip() for c in df.columns]
                    if df.apply(
                        lambda col: col.str.contains("VALIDATED", na=False)
                    ).any().any():
                        return True
                except Exception:
                    continue
        return False
    except Exception:
        return False

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

def est_kiosk_photo(fichier: Path) -> bool:
    return (
        fichier.suffix.lower() == ".csv"
        and "_ventes" in fichier.stem.lower()
    )

# ============================================================================
# DETECTEURS MODULE 2
# ============================================================================

def est_banque_internet(fichier: Path) -> bool:
    if fichier.suffix.lower() not in [".xls", ".xlsx"]:
        return False
    try:
        engine = _get_engine(fichier)
        df = pd.read_excel(
            fichier, header=None, engine=engine, nrows=200, dtype=str
        )
        if df.shape[1] < 2:
            return False
        col_b = df[1].astype(str).str.strip()
        return col_b.isin(CONTRATS_BANQUE.keys()).any()
    except Exception as e:
        logger.debug(f"est_banque_internet({fichier.name}) : {e}")
        return False

def est_alpilink(fichier: Path) -> bool:
    return (
        fichier.suffix.lower() in [".xls", ".xlsx"]
        and fichier.stem.lower().startswith("data")
    )

def est_compta_internet(fichier: Path) -> bool:
    try:
        fichier = Path(fichier)
        if fichier.suffix.lower() not in [".xls", ".xlsx"]:
            return False
        nom_fichier = fichier.name.lower()
        if nom_fichier.startswith("fr_") and "statement" in nom_fichier:
            return False
        if "pmt internet" not in nom_fichier and "interr" not in nom_fichier:
            return False
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, engine=engine, nrows=10)
        colonnes = [
            str(c).strip().lower().replace(" ", "") for c in df.columns
        ]
        colonnes_requises = ["date", "libell", "montant", "journal", "débit", "crédit"]
        count = sum(
            1 for motif in colonnes_requises
            if any(motif in col for col in colonnes)
        )
        if count >= 3:
            logger.info(f"COMPTA INTERNET détecté : {fichier.name}")
            return True
        return False
    except Exception as e:
        logger.error(f"est_compta_internet({fichier.name}) : {e}")
        return False

# ============================================================================
# EXPORTS
# ============================================================================

def get_engine(fichier: Path) -> Literal["xlrd", "openpyxl"]:
    return _get_engine(fichier)

__all__ = [
    "get_engine",
    "_get_engine",
    # Module 1
    "est_amex_caisse",
    "est_amex_internet",
    "est_alma",
    "est_ancv",
    "est_ancv_banque",
    "est_avoirs",
    "est_kiosk_photo",
    "est_ta",
    "est_planet",
    "est_planet_caisse",
    "est_planet_internet",
    # Module 2
    "est_banque_internet",
    "est_alpilink",
    "est_compta_internet",
]
