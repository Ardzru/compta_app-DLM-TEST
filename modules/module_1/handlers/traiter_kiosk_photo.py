# handlers/module_1/traiter_kiosk_photo.py
"""
Module 1 : Traitement KIOSK PHOTO
"""

import pandas as pd
from pathlib import Path
from typing import Optional

from config import DOSSIER_SORTIE, logger

from core.utils.montant import to_float, format_montant
from core.utils.date import formater_date
from core.utils.colonnes import STE_DEFAUT, COLONNES_SORTIE
from core.utils.constantes import (
    COMPTE_BANQUE,
    COMPTE_TVA,
    COMPTE_PRODUITS,
    JOURNAUX,
)

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotKioskPhotoFileError(Exception):
    """Levée si aucun kiosk photo exploitable n'est trouvé."""
    pass

# ==========================================================
# CONSTANTES COLONNES KIOSK PHOTO (SPÉCIFIQUES AU MODULE)
# ==========================================================

KIOSK_PHOTO_COL = {
    "date": "Date",
    "num_txn": "Transaction",
    "montant_brut": "Montant Brut",
    "tva": "TVA",
    "montant_net": "Montant Net",
    "libelle": "Libellé",
    "type_monnayeur": "Type",
}

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_kiosk_photo(fichier: Path) -> Optional[Path]:
    """
    Traite un fichier KIOSK PHOTO et génère les écritures comptables.

    Règles métier :
    - Débit monnayeur/TPE
    - Crédit TVA collectée (44571)
    - Crédit Produits ventes (706)

    Returns:
        Path: Chemin du fichier généré
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier KIOSK PHOTO introuvable : {fichier}")

    logger.info(f"Traitement KIOSK PHOTO : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture + validation
    # ----------------------------------------------------------
    df = pd.read_excel(fichier)

    if df.empty:
        logger.error(f"Fichier vide : {fichier.name}")
        return None

    logger.info(f"Lignes lues : {len(df)}")

    # ----------------------------------------------------------
    # 2. Parcours des lignes
    # ----------------------------------------------------------
    transactions: dict = {}
    nb_ignores = 0

    for idx, row in df.iterrows():
        try:
            date_str = str(row[KIOSK_PHOTO_COL["date"]]).strip()
            date_compta = formater_date(date_str)
            num_txn = str(row[KIOSK_PHOTO_COL["num_txn"]]).strip()
            montant_brut = to_float(row[KIOSK_PHOTO_COL["montant_brut"]])
            tva = to_float(row[KIOSK_PHOTO_COL["tva"]])
            montant_net = to_float(row[KIOSK_PHOTO_COL["montant_net"]])
            libelle = str(row[KIOSK_PHOTO_COL["libelle"]]).strip()
            type_monnayeur = str(row[KIOSK_PHOTO_COL["type_monnayeur"]]).strip()

            if not date_compta or montant_brut == 0:
                nb_ignores += 1
                continue

            # Déterminer le compte de débit selon le type
            if "TPE" in type_monnayeur.upper():
                compte_debit = "5121"  # TPE Carte
            else:
                compte_debit = "5301"  # Caisses

            transactions[num_txn] = {
                "date": date_compta,
                "montant_brut": round(montant_brut, 2),
                "tva": round(tva, 2),
                "montant_net": round(montant_net, 2),
                "libelle": libelle,
                "compte_debit": compte_debit,
            }

        except Exception as e:
            logger.warning(f"Ligne {idx} ignorée : {str(e)}")
            nb_ignores += 1
            continue

    logger.info(f"Transactions trouvées : {len(transactions)} | Ignorés : {nb_ignores}")

    if not transactions:
        logger.warning(f"Aucune transaction KIOSK PHOTO à traiter dans {fichier.name}")
        return None

    # ----------------------------------------------------------
    # 3. Construction des écritures
    # ----------------------------------------------------------
    lignes_finales = []

    for num_txn, data in sorted(transactions.items()):
        date_compta = data["date"]
        montant_brut = data["montant_brut"]
        tva = data["tva"]
        montant_net = data["montant_net"]
        libelle = data["libelle"]
        compte_debit = data["compte_debit"]

        # Ligne 1 : Débit compte monnayeur/TPE
        lignes_finales.append({
            "STE": STE_DEFAUT,
            "DATE": date_compta,
            "COMPTE": compte_debit,
            "Auxiliaire": "",
            "n°pièce": f"KIOSK-{num_txn}",
            "OBJET": f"Vente photos {libelle}",
            "D": format_montant(montant_net),
            "C": "",
            "Journal": JOURNAUX["kiosk_photo"],
            "Analytique": "",
        })

        # Ligne 2 : Crédit TVA collectée
        if tva > 0:
            lignes_finales.append({
                "STE": STE_DEFAUT,
                "DATE": date_compta,
                "COMPTE": COMPTE_TVA,
                "Auxiliaire": "",
                "n°pièce": f"KIOSK-{num_txn}",
                "OBJET": f"TVA collectée - {libelle}",
                "D": "",
                "C": format_montant(tva),
                "Journal": JOURNAUX["kiosk_photo"],
                "Analytique": "",
            })

        # Ligne 3 : Crédit Produits ventes
        montant_produit = round(montant_brut - tva, 2)
        lignes_finales.append({
            "STE": STE_DEFAUT,
            "DATE": date_compta,
            "COMPTE": COMPTE_PRODUITS,
            "Auxiliaire": "",
            "n°pièce": f"KIOSK-{num_txn}",
            "OBJET": f"Produits ventes photos - {libelle}",
            "D": "",
            "C": format_montant(montant_produit),
            "Journal": JOURNAUX["kiosk_photo"],
            "Analytique": "ST-CT00-XX",
        })

    if not lignes_finales:
        logger.warning(f"Aucune écriture générée pour {fichier.name}")
        return None

    # ----------------------------------------------------------
    # 4. Export CSV
    # ----------------------------------------------------------
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    df_final = pd.DataFrame(lignes_finales)
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_kiosk_photo.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export KIOSK PHOTO : {sortie.name} ({len(lignes_finales)} écritures)")

    return sortie

# ==========================================================
# CLASSE HANDLER
# ==========================================================

class TraiterKioskPhotoHandler:
    """Handler pour traiter les fichiers KIOSK PHOTO."""

    @staticmethod
    def traiter(fichier: Path) -> None:
        """Traite un fichier KIOSK PHOTO."""
        traiter_kiosk_photo(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """Vérifie si c'est un fichier KIOSK PHOTO."""
        return detecteur_result.get("type") == "kiosk_photo"

__all__ = ['TraiterKioskPhotoHandler', 'traiter_kiosk_photo']
