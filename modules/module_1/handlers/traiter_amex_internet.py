"""
Module 1 — Handler AMEX INTERNET
Traite fichiers AMEX Internet → écritures comptables CSV.
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Tuple

from config import DOSSIER_SORTIE, logger

# ✅ IMPORTS CORE
from core.utils.montant import format_montant_compta
from core.utils.date import formater_date_fr
from core.utils.constantes import (
    STE_DLM,
    JOURNAL_CEBOOBA,
    COLONNES_SORTIE,
    COMPTE_TRANSIT,
    COMPTE_FRAIS_AMEX,
    COMPTE_BANQUE,
    ANALYTIQUE_FRAIS,
)

# ============================================================
# CONSTANTES — INDICES COLONNES AMEX INTERNET
# ============================================================

COL_DATE_LIB = 0  # Date affichée (libellé)
COL_DATE_COMPTA = 13  # Date comptable
COL_D = 3  # Montant brut
COL_E = 4  # Montant crédité / débité
COL_G = 6  # Frais AMEX
COL_I = 8  # Montant net
COL_LIEU = 14  # Nom du lieu (ex: "DLM SITE WEB")

# ============================================================
# UTILITAIRES PRIVÉS
# ============================================================

def _nettoyer_montant(val) -> float:
    """Nettoie et convertit un montant AMEX en float."""
    if pd.isna(val):
        return 0.0

    s = str(val).strip()
    s = s.replace(" ", "").replace(".", "").replace(",", ".")

    if s.endswith("-"):
        s = "-" + s[:-1]

    try:
        return float(s)
    except ValueError:
        return 0.0

def _extraire_lieu(val) -> str:
    """Extrait et nettoie le lieu (colonne 14)."""
    if pd.isna(val):
        return ""
    return str(val).strip().upper()

# ============================================================
# HANDLER PRINCIPAL
# ============================================================

def traiter_amex_internet(fichier: Path) -> Tuple[str, str]:
    """
    Traite un fichier AMEX Internet → écritures comptables CSV.

    Filtre : seules lignes avec "SITE" en colonne 14
    Génère 3 types d'écritures selon les frais AMEX.
    """

    fichier = Path(fichier)
    if not fichier.exists():
        msg = f"Fichier AMEX Internet introuvable : {fichier}"
        logger.error(f"[AMEX_INTERNET] ❌ {msg}")
        raise FileNotFoundError(msg)

    try:
        df = pd.read_excel(fichier, header=None, engine="openpyxl")

    except Exception as e:
        msg = f"Impossible de lire {fichier.name} : {e}"
        logger.error(f"[AMEX_INTERNET] ❌ {msg}", exc_info=True)
        return "ERREUR", msg

    # Parcours et accumulation par date comptable
    groupes: dict = defaultdict(lambda: {"lignes": [], "total_banque": 0.0})
    lignes_finales = []
    piece = "AMEX INTERNET"

    for idx, row in df.iterrows():
        # ✅ FILTRE SITE — colonne 14
        lieu = _extraire_lieu(row[COL_LIEU])

        if "SITE" not in lieu:
            continue

        # Dates
        date_lib = formater_date_fr(row[COL_DATE_LIB])
        date_compta = formater_date_fr(row[COL_DATE_COMPTA])

        if not date_lib or not date_compta:
            continue

        # Montants
        D = _nettoyer_montant(row[COL_D])
        E = _nettoyer_montant(row[COL_E])
        G = _nettoyer_montant(row[COL_G])
        I = _nettoyer_montant(row[COL_I])

        # Filtre zéro
        if D == 0 and E == 0 and G == 0 and I == 0:
            continue

        groupe = groupes[date_compta]

        # ──────────────────────────────────────────────────
        # CAS 1 — REMBOURSEMENT CLIENT (E < 0, G == 0)
        # ──────────────────────────────────────────────────
        if E < 0 and G == 0:
            montant = abs(E)

            groupe["lignes"].append({
                "STE": STE_DLM,
                "DATE": date_compta,
                "COMPTE": COMPTE_TRANSIT,
                "Auxiliaire": "",
                "n°pièce": piece,
                "OBJET": f"AMEX INTERNET DU {date_lib}",
                "D": format_montant_compta(montant),
                "C": "",
                "Journal": JOURNAL_CEBOOBA,
                "Analytique": "",
            })

            groupe["total_banque"] -= montant

        # ──────────────────────────────────────────────────
        # CAS 2 — ENCAISSEMENT SIMPLE (E > 0, G == 0)
        # ──────────────────────────────────────────────────
        elif E > 0 and G == 0:

            groupe["lignes"].append({
                "STE": STE_DLM,
                "DATE": date_compta,
                "COMPTE": COMPTE_TRANSIT,
                "Auxiliaire": "",
                "n°pièce": piece,
                "OBJET": f"AMEX INTERNET DU {date_lib}",
                "D": "",
                "C": format_montant_compta(E),
                "Journal": JOURNAL_CEBOOBA,
                "Analytique": "",
            })

            groupe["total_banque"] += I

        # ──────────────────────────────────────────────────
        # CAS 3 — ENCAISSEMENT AVEC FRAIS AMEX (G > 0)
        # ──────────────────────────────────────────────────
        else:

            groupe["lignes"].append({
                "STE": STE_DLM,
                "DATE": date_compta,
                "COMPTE": COMPTE_TRANSIT,
                "Auxiliaire": "",
                "n°pièce": piece,
                "OBJET": f"AMEX INTERNET DU {date_lib}",
                "D": "",
                "C": format_montant_compta(D),
                "Journal": JOURNAL_CEBOOBA,
                "Analytique": "",
            })

            groupe["lignes"].append({
                "STE": STE_DLM,
                "DATE": date_compta,
                "COMPTE": COMPTE_FRAIS_AMEX,
                "Auxiliaire": "",
                "n°pièce": piece,
                "OBJET": f"FRAIS AMEX - {piece}",
                "D": format_montant_compta(G),
                "C": "",
                "Journal": JOURNAL_CEBOOBA,
                "Analytique": ANALYTIQUE_FRAIS,
            })

            groupe["total_banque"] += I

    # Génération finale : une ligne banque par date comptable
    for date_compta, groupe in sorted(groupes.items()):

        lignes_finales.extend(groupe["lignes"])

        total_banque = round(groupe["total_banque"], 2)

        if total_banque == 0.0:
            continue

        objet_banque = (
            groupe["lignes"][0]["OBJET"]
            if groupe["lignes"]
            else f"AMEX INTERNET DU {date_compta}"
        )

        lignes_finales.append({
            "STE": STE_DLM,
            "DATE": date_compta,
            "COMPTE": COMPTE_BANQUE,
            "Auxiliaire": "",
            "n°pièce": piece,
            "OBJET": objet_banque,
            "D": format_montant_compta(total_banque) if total_banque > 0 else "",
            "C": format_montant_compta(-total_banque) if total_banque < 0 else "",
            "Journal": JOURNAL_CEBOOBA,
            "Analytique": "",
        })

    # Export CSV
    if not lignes_finales:
        msg = f"Aucune écriture générée pour {fichier.name}"
        return "AUCUNE_DONNEE", msg

    try:
        DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

        df_final = pd.DataFrame(lignes_finales)
        sortie = DOSSIER_SORTIE / f"{fichier.stem}_amex_internet.csv"
        df_final.to_csv(
            sortie,
            sep=";",
            index=False,
            encoding="latin1",
            columns=COLONNES_SORTIE,
        )

        return "OK", str(sortie)

    except Exception as e:
        msg = f"Erreur export CSV : {e}"
        logger.error(f"[AMEX_INTERNET] ❌ {msg}", exc_info=True)
        return "ERREUR", msg

__all__ = ["traiter_amex_internet"]
