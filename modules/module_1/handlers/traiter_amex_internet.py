# handlers/module_2/traiter_amex_internet.py
"""
Module 2 : Traitement AMEX INTERNET
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from collections import defaultdict
from datetime import datetime, timedelta

from config import DOSSIER_SORTIE, logger

from core.utils.montant import to_float, format_montant
from core.utils.date import formater_date
from core.utils.colonnes import STE_DEFAUT, COLONNES_SORTIE
from core.utils.constantes import (
    COMPTE_TRANSIT,
    COMPTE_BANQUE,
    JOURNAUX,
)

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotAmexInternetFileError(Exception):
    """Levée si aucune ligne AMEX INTERNET exploitable n'est trouvée."""
    pass

# ==========================================================
# CONSTANTES COLONNES AMEX INTERNET (SPÉCIFIQUES AU MODULE)
# ==========================================================

AMEX_INTERNET_COL = {
    "date_saisie": 0,
    "date_compta": 1,
    "reference": 2,
    "montant": 3,
    "motif": 4,
    "type": 5,
}

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_amex_internet(fichier: Path) -> Optional[Path]:
    """
    Traite un fichier AMEX INTERNET et génère les écritures comptables.

    Règles métier :
    - Ventes → COMPTE_TRANSIT (crédit)
    - Encaissements → COMPTE_BANQUE (débit)
    - Frais AMEX → COMPTE_FOURN (débit)

    Returns:
        Path: Chemin du fichier généré
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier AMEX INTERNET introuvable : {fichier}")

    logger.info(f"Traitement AMEX INTERNET : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture + validation
    # ----------------------------------------------------------
    df = pd.read_excel(fichier)

    if df.empty:
        logger.error(f"Fichier vide : {fichier.name}")
        return None

    logger.info(f"Lignes lues : {len(df)}")

    # ----------------------------------------------------------
    # 2. Regroupement par date comptable
    # ----------------------------------------------------------
    groupes: dict = defaultdict(lambda: {
        "lignes": [],
        "total_transit": 0.0,
        "total_banque": 0.0,
    })
    nb_ignores = 0

    for idx, row in df.iterrows():
        try:
            date_lib = formater_date(row[AMEX_INTERNET_COL["date_saisie"]])
            date_compta = formater_date(row[AMEX_INTERNET_COL["date_compta"]])
            reference = str(row[AMEX_INTERNET_COL["reference"]]).strip()
            montant = to_float(row[AMEX_INTERNET_COL["montant"]])
            motif = str(row[AMEX_INTERNET_COL["motif"]]).strip().upper()
            type_txn = str(row[AMEX_INTERNET_COL["type"]]).strip().upper()

            if not date_compta or montant == 0:
                nb_ignores += 1
                continue

            piece = f"AMEX-{reference}"

            # ------ CAS 1 — VENTE SANS FRAIS ------
            if type_txn == "VENTE" and "SANS FRAIS" in motif:
                groupe = groupes[date_compta]

                # Débit transit, crédit banque
                groupe["lignes"].append({
                    "STE": STE_DEFAUT,
                    "DATE": date_compta,
                    "COMPTE": COMPTE_TRANSIT,
                    "Auxiliaire": "",
                    "n°pièce": piece,
                    "OBJET": f"AMEX INTERNET DU {date_lib}",
                    "D": format_montant(montant),
                    "C": "",
                    "Journal": JOURNAUX["amex_internet"],
                    "Analytique": "",
                })

                groupe["total_banque"] += montant

            # ------ CAS 2 — VENTE AVEC FRAIS ------
            elif type_txn == "VENTE" and "AVEC FRAIS" in motif:
                groupe = groupes[date_compta]
                montant_net = montant

                groupe["lignes"].append({
                    "STE": STE_DEFAUT,
                    "DATE": date_compta,
                    "COMPTE": COMPTE_TRANSIT,
                    "Auxiliaire": "",
                    "n°pièce": piece,
                    "OBJET": f"AMEX INTERNET DU {date_lib}",
                    "D": "",
                    "C": format_montant(montant),
                    "Journal": JOURNAUX["amex_internet"],
                    "Analytique": "",
                })

                groupe["total_banque"] += montant_net

        except Exception as e:
            logger.warning(f"Ligne {idx} ignorée : {str(e)}")
            nb_ignores += 1
            continue

    logger.info(f"Groupes trouvés : {len(groupes)} | Ignorés : {nb_ignores}")

    if not groupes:
        logger.warning(f"Aucune écriture AMEX INTERNET à traiter dans {fichier.name}")
        return None

    # ----------------------------------------------------------
    # 3. Génération écritures finales
    # ----------------------------------------------------------
    lignes_finales = []

    for date_compta, groupe in sorted(groupes.items()):
        lignes_finales.extend(groupe["lignes"])

        # Ligne banque
        if groupe["total_banque"] != 0:
            lignes_finales.append({
                "STE": STE_DEFAUT,
                "DATE": date_compta,
                "COMPTE": COMPTE_BANQUE,
                "Auxiliaire": "",
                "n°pièce": f"AMEX-{date_compta.replace('/', '')}",
                "OBJET": f"Encaissement AMEX INTERNET",
                "D": format_montant(groupe["total_banque"]),
                "C": "",
                "Journal": JOURNAUX["amex_internet"],
                "Analytique": "",
            })

    if not lignes_finales:
        logger.warning(f"Aucune écriture générée pour {fichier.name}")
        return None

    # ----------------------------------------------------------
    # 4. Export CSV
    # ----------------------------------------------------------
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    df_final = pd.DataFrame(lignes_finales)
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_amex_internet.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export AMEX INTERNET : {sortie.name} ({len(lignes_finales)} écritures)")

    return sortie

# ==========================================================
# CLASSE HANDLER
# ==========================================================

class TraiterAmexInternetHandler:
    """Handler pour traiter les fichiers AMEX INTERNET."""

    @staticmethod
    def traiter(fichier: Path) -> None:
        """Traite un fichier AMEX INTERNET."""
        traiter_amex_internet(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """Vérifie si c'est un fichier AMEX INTERNET."""
        return detecteur_result.get("type") == "amex_internet"

__all__ = ['TraiterAmexInternetHandler', 'traiter_amex_internet']
