# handlers/module_1/traiter_planet.py
"""
Module 1 : Traitement PLANET
"""

import csv
import openpyxl
from pathlib import Path
from typing import Optional
from collections import defaultdict

from config import DOSSIER_SORTIE, logger

from core.utils.montant import to_float, format_montant
from core.utils.date import formater_date, date_en_cle
from core.utils.colonnes import STE_DEFAUT, COLONNES_SORTIE
from core.utils.constantes import (
    COMPTE_BANQUE,
    COMPTE_TRANSIT,
    COMPTE_FOURN,
    AUX_PLANET,
    JOURNAUX,
    PLANET_COL,
)

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotPlanetFileError(Exception):
    """Levée si le fichier ne contient aucune ligne PLANET exploitable."""
    pass

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_planet(fichier: Path) -> Optional[Path]:
    """
    Traite un fichier PLANET et génère les écritures comptables.

    Règles métier :
    - Regroupement par lot
    - Brut → COMPTE_BANQUE (512120)
    - Commissions/TVA → COMPTE_FOURN (401000)
    - Ventes → COMPTE_TRANSIT (580010DS5)

    Returns:
        Path: Chemin du fichier généré
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier PLANET introuvable : {fichier}")

    logger.info(f"Traitement PLANET : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture du fichier
    # ----------------------------------------------------------
    try:
        # Détecte le format (CSV ou XLSX)
        if fichier.suffix.lower() == ".xlsx":
            df = pd.read_excel(fichier)
        else:
            df = pd.read_csv(fichier, sep=";", encoding="latin1")
    except Exception as e:
        logger.error(f"Erreur lecture PLANET : {str(e)}")
        raise

    if df.empty:
        logger.error(f"Fichier vide : {fichier.name}")
        return None

    logger.info(f"Lignes lues : {len(df)}")

    # ----------------------------------------------------------
    # 2. Parcours et regroupement par lot
    # ----------------------------------------------------------
    lots: dict = defaultdict(lambda: {
        "Sale": [],
        "Refund": [],
        "date": None,
        "date_cle": None,
        "date_txn": None,
    })
    nb_ignores = 0

    for idx, row in df.iterrows():
        try:
            type_txn = str(row[PLANET_COL["type"]]).strip().upper() if row[PLANET_COL["type"]] else ""

            if type_txn not in ("SALE", "REFUND"):
                nb_ignores += 1
                continue

            lot_id = str(row[PLANET_COL["lot"]]).strip() if row[PLANET_COL["lot"]] else ""
            brut = to_float(row[PLANET_COL["brut"]])
            comm = to_float(row[PLANET_COL["comm"]])
            tva = to_float(row[PLANET_COL["tva"]])
            libel = str(row[PLANET_COL["libel"]]).strip() if row[PLANET_COL["libel"]] else ""
            date_txn = formater_date(row[PLANET_COL["date_txn"]])  # date transaction → libellé
            date_val = formater_date(row[PLANET_COL["date_val"]])  # date valeur → date comptable
            dcle = date_en_cle(row[PLANET_COL["date_val"]])

            if not lot_id or brut == 0:
                nb_ignores += 1
                continue

            lots[lot_id][type_txn].append({
                "brut": brut,
                "comm": comm,
                "tva": tva,
                "libelle": libel,
            })

            # On garde la dernière date rencontrée pour le lot
            lots[lot_id]["date"] = date_val
            lots[lot_id]["date_cle"] = dcle
            lots[lot_id]["date_txn"] = date_txn

        except Exception as e:
            logger.warning(f"Ligne {idx} ignorée : {str(e)}")
            nb_ignores += 1
            continue

    logger.info(f"Lots trouvés : {len(lots)} | Ignorés : {nb_ignores}")

    if not lots:
        logger.warning(f"Aucun lot PLANET à traiter dans {fichier.name}")
        return None

    # ----------------------------------------------------------
    # 3. Construction des écritures comptables
    # ----------------------------------------------------------
    lignes_sortie = []

    for lot_id, types in sorted(lots.items(), key=lambda x: x[1]["date_cle"] or ""):

        date_lot = types["date"]
        date_txn = types.get("date_txn", date_lot)
        n_piece = f"PLANET{lot_id}"

        # Calculs par type
        brut_sales = sum(item["brut"] for item in types["Sale"])
        brut_refunds = sum(item["brut"] for item in types["Refund"])
        comm_sales = sum(item["comm"] for item in types["Sale"])
        comm_refunds = sum(item["comm"] for item in types["Refund"])
        tva_sales = sum(item["tva"] for item in types["Sale"])
        tva_refunds = sum(item["tva"] for item in types["Refund"])

        brut_net = round(brut_sales - brut_refunds, 2)
        comm_net = round(comm_sales - comm_refunds, 2)
        tva_net = round(tva_sales - tva_refunds, 2)
        charges_ttc = round(comm_net + tva_net, 2)
        montant_net = round(brut_net - charges_ttc, 2)

        # ------ Ligne 1 : BANQUE (débit) ------
        if brut_net != 0:
            lignes_sortie.append({
                "STE": STE_DEFAUT,
                "DATE": date_lot,
                "COMPTE": COMPTE_BANQUE,
                "Auxiliaire": "",
                "n°pièce": n_piece,
                "OBJET": f"PLANET {date_txn}",
                "D": format_montant(montant_net) if montant_net > 0 else "",
                "C": format_montant(abs(montant_net)) if montant_net < 0 else "",
                "Journal": JOURNAUX["planet"],
                "Analytique": "",
            })

        # ------ Ligne 2 : FOURNISSEUR PLANET (crédit) ------
        if charges_ttc != 0:
            lignes_sortie.append({
                "STE": STE_DEFAUT,
                "DATE": date_lot,
                "COMPTE": COMPTE_FOURN,
                "Auxiliaire": AUX_PLANET,
                "n°pièce": n_piece,
                "OBJET": f"Commissions + TVA PLANET",
                "D": format_montant(charges_ttc) if charges_ttc > 0 else "",
                "C": format_montant(abs(charges_ttc)) if charges_ttc < 0 else "",
                "Journal": JOURNAUX["planet"],
                "Analytique": "",
            })

        # ------ Ligne 3 : TRANSIT (crédit) ------
        if brut_net != 0:
            lignes_sortie.append({
                "STE": STE_DEFAUT,
                "DATE": date_lot,
                "COMPTE": COMPTE_TRANSIT,
                "Auxiliaire": "",
                "n°pièce": n_piece,
                "OBJET": f"Ventes PLANET {date_txn}",
                "D": "",
                "C": format_montant(brut_net) if brut_net > 0 else "",
                "Journal": JOURNAUX["planet"],
                "Analytique": "",
            })

    if not lignes_sortie:
        logger.warning(f"Aucune écriture générée pour {fichier.name}")
        return None

    # ----------------------------------------------------------
    # 4. Export CSV
    # ----------------------------------------------------------
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    df_final = pd.DataFrame(lignes_sortie)
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_planet.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export PLANET : {sortie.name} ({len(lignes_sortie)} écritures)")

    return sortie

# ==========================================================
# CLASSE HANDLER
# ==========================================================

class TraiterPlanetHandler:
    """Handler pour traiter les fichiers PLANET."""

    @staticmethod
    def traiter(fichier: Path) -> None:
        """Traite un fichier PLANET."""
        traiter_planet(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """Vérifie si c'est un fichier PLANET."""
        return detecteur_result.get("type") == "planet"

__all__ = ['TraiterPlanetHandler', 'traiter_planet']
