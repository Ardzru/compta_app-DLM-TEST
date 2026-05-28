# handlers/module_1/traiter_avoirs.py
"""
Module 1 : Traitement AVOIRS
"""

import pandas as pd
from pathlib import Path
from typing import Optional

from config import DOSSIER_SORTIE, logger

from core.utils.montant import to_float, format_montant
from core.utils.date import formater_date
from core.utils.colonnes import STE_DEFAUT, COLONNES_SORTIE
from core.utils.constantes import (
    COMPTE_COMMANDE,
    JOURNAUX,
)
from core.moniteur_schema import comparer_schema

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotAvoirFileError(Exception):
    """Levée si aucun avoir exploitable n'est trouvé."""
    pass

# ==========================================================
# CONSTANTES COLONNES AVOIRS (SPÉCIFIQUES AU MODULE)
# ==========================================================

AVOIRS_COLONNES = {
    "num_avoir": "Numéro avoir",
    "date": "Date avoir",
    "client": "Client",
    "montant": "Montant",
    "motif": "Motif",
}

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_avoirs(fichier: Path) -> Optional[Path]:
    """
    Traite un fichier AVOIRS et génère les écritures comptables.

    Règles métier :
    - Annulation de vente → Crédit COMPTE_COMMANDE
    - Une ligne par avoir

    Returns:
        Path: Chemin du fichier généré
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier AVOIRS introuvable : {fichier}")

    logger.info(f"Traitement AVOIRS : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture + validation schéma
    # ----------------------------------------------------------
    df = pd.read_excel(fichier)

    if df.empty:
        logger.error(f"Fichier vide : {fichier.name}")
        return None

    comparer_schema(df, "avoirs")

    logger.info(f"Colonnes trouvées : {list(df.columns)}")

    # ----------------------------------------------------------
    # 2. Parcours des lignes
    # ----------------------------------------------------------
    avoirs: dict = {}  # { num_avoir: {"date": str, "montant": float, "client": str} }
    total_avoirs = 0.0
    nb_ignores = 0

    for idx, row in df.iterrows():
        try:
            num_avoir = str(row[AVOIRS_COLONNES["num_avoir"]]).strip()
            date_avoir = formater_date(row[AVOIRS_COLONNES["date"]])
            client = str(row[AVOIRS_COLONNES["client"]]).strip()
            montant = to_float(row[AVOIRS_COLONNES["montant"]])

            if not date_avoir:
                logger.debug(f"Ligne {idx} ignorée : date invalide")
                nb_ignores += 1
                continue

            if montant <= 0:
                logger.debug(f"Ligne {idx} ignorée : montant négatif ou nul")
                nb_ignores += 1
                continue

            avoirs[num_avoir] = {
                "date": date_avoir,
                "montant": round(montant, 2),
                "client": client,
            }
            total_avoirs += montant

        except Exception as e:
            logger.warning(f"Ligne {idx} ignorée : {str(e)}")
            nb_ignores += 1
            continue

    if not avoirs:
        logger.warning(f"Aucun avoir à traiter dans {fichier.name}")
        return None

    logger.info(f"Avoirs trouvés : {len(avoirs)} | Ignorés : {nb_ignores} | Total : {format_montant(total_avoirs)}")

    # ----------------------------------------------------------
    # 3. Construction des écritures
    # ----------------------------------------------------------
    lignes_finales = []

    for num_avoir, data in sorted(avoirs.items()):
        date_compta = data["date"]
        montant = data["montant"]
        client = data["client"]

        # Ligne : Annulation vente
        lignes_finales.append({
            "STE": STE_DEFAUT,
            "DATE": date_compta,
            "COMPTE": COMPTE_COMMANDE,
            "Auxiliaire": client,
            "n°pièce": f"AV-{num_avoir}",
            "OBJET": f"Annulation vente - Avoir {num_avoir}",
            "D": "",
            "C": format_montant(montant),
            "Journal": JOURNAUX["avoirs"],
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
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_avoirs.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export AVOIRS : {sortie.name} ({len(lignes_finales)} écritures)")

    return sortie

# ==========================================================
# CLASSE HANDLER
# ==========================================================

class TraiterAvoirsHandler:
    """Handler pour traiter les fichiers AVOIRS."""

    @staticmethod
    def traiter(fichier: Path) -> None:
        """Traite un fichier AVOIRS."""
        traiter_avoirs(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """Vérifie si c'est un fichier AVOIRS."""
        return detecteur_result.get("type") == "avoirs"

__all__ = ['TraiterAvoirsHandler', 'traiter_avoirs']
