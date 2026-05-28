# handlers/module_2/traiter_amex_caisse.py
"""
Module 2 : Traitement AMEX CAISSE pour justification compte caisse
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from collections import defaultdict

from config import DOSSIER_SORTIE, FICHIER_CORRESPONDANCE_AMEX
from config import logger

from core.utils.montant import to_float, format_montant
from core.utils.date import formater_date
from core.utils.colonnes import STE_DEFAUT
from core.utils.constantes import JOURNAUX
from core.moniteur_schema import comparer_schema

# ==========================================================
# COLONNES SOURCES AMEX CAISSE
# ==========================================================
AMEX_CAISSE_COLONNES = {
    "date_reglement": "Date Règlement",
    "date_transaction": "Date Transaction",
    "type": "Type",
    "num_ref": "N°Référence",
    "num_reglement": "N°Règlement",
    "montant_brut": "Montant Brut",
    "frais": "Frais",
    "montant_net": "Montant Net",
    "roc_id_terminal": "ROC ID Terminal",
}

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotAmexCaisseFileError(Exception):
    """Levée si aucune ligne AMEX CAISSE exploitable n'est trouvée."""
    pass

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_amex_caisse(fichier: Path) -> Optional[Path]:
    """
    Traite un fichier AMEX CAISSE et génère les écritures comptables
    pour justification du compte caisse.

    Règles métier :
    - Montant brut → Débit 512121 (caisse AMEX)
    - Frais AMEX → Débit 627800
    - Contrepartie → Crédit 512120 (banque)

    Returns:
        Path: Chemin du fichier généré
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier AMEX CAISSE introuvable : {fichier}")

    logger.info(f"Traitement AMEX CAISSE : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture + validation schéma
    # ----------------------------------------------------------
    df = pd.read_csv(fichier, sep=";", encoding="latin1")

    if df.empty:
        logger.error(f"Fichier vide : {fichier.name}")
        raise NotAmexCaisseFileError(f"Fichier vide : {fichier.name}")

    comparer_schema(df, "amex_caisse")

    logger.info(f"Colonnes trouvées : {list(df.columns)}")

    # ----------------------------------------------------------
    # 2. Parcours des lignes
    # ----------------------------------------------------------
    groupes: dict = {}  # { (date_compta, num_caisse): {"lignes": [], "total_net": float} }
    total_general = 0.0

    for idx, row in df.iterrows():
        date_transaction = formater_date(row[AMEX_CAISSE_COLONNES["date_transaction"]])
        num_ref = str(row[AMEX_CAISSE_COLONNES["num_ref"]]).strip()
        montant_brut = to_float(row[AMEX_CAISSE_COLONNES["montant_brut"]])
        frais = to_float(row[AMEX_CAISSE_COLONNES["frais"]])
        montant_net = to_float(row[AMEX_CAISSE_COLONNES["montant_net"]])

        if montant_brut <= 0:
            logger.debug(f"Ligne {idx} ignorée : montant brut négatif ou nul")
            continue

        cle_groupe = (date_transaction, num_ref[:2])  # Première 2 chars du num_ref
        if cle_groupe not in groupes:
            groupes[cle_groupe] = {"lignes": [], "total_net": 0.0}

        date_compta = date_transaction
        num_piece = f"AMEX-{num_ref}"
        libelle = f"AMEX {AMEX_CAISSE_COLONNES['type']}"

        # Ligne 1 : Montant brut caisse AMEX
        groupes[cle_groupe]["lignes"].append({
            "STE": STE_DEFAUT,
            "DATE": date_compta,
            "COMPTE": "512121",
            "Auxiliaire": "",
            "n°pièce": num_piece,
            "OBJET": f"Encaissement AMEX - {libelle}",
            "D": format_montant(montant_brut),
            "C": "",
            "Journal": JOURNAUX["amex_caisse"],
            "Analytique": "",
        })

        # Ligne 2 : Frais AMEX
        if frais != 0.0:
            groupes[cle_groupe]["lignes"].append({
                "STE": STE_DEFAUT,
                "DATE": date_compta,
                "COMPTE": "627800",
                "Auxiliaire": "",
                "n°pièce": num_piece,
                "OBJET": f"Frais AMEX - {libelle}",
                "D": format_montant(abs(frais)),
                "C": "",
                "Journal": JOURNAUX["amex_caisse"],
                "Analytique": "ST-CT00-XX",
            })

        groupes[cle_groupe]["total_net"] += montant_net
        total_general += montant_net

    if not groupes:
        logger.error(f"Aucune ligne exploitable dans {fichier.name}")
        raise NotAmexCaisseFileError(f"Aucune ligne exploitable : {fichier.name}")

    logger.info(f"Transactions AMEX : {sum(len(g['lignes']) for g in groupes.values())} écritures")

    # ----------------------------------------------------------
    # 3. Génération finale avec contrepartie
    # ----------------------------------------------------------
    lignes_finales = []
    par_date: dict = defaultdict(lambda: {"lignes": [], "total_net": 0.0})

    for (date_compta, _), groupe in sorted(groupes.items()):
        par_date[date_compta]["lignes"].extend(groupe["lignes"])
        par_date[date_compta]["total_net"] += groupe["total_net"]

    for date_compta, data in sorted(par_date.items()):
        lignes_finales.extend(data["lignes"])
        total_net = round(data["total_net"], 2)

        if total_net == 0.0:
            logger.warning(f"Total net nul pour {date_compta}, contrepartie ignorée")
            continue

        # Contrepartie banque
        cle_date_banque = date_compta[6:] + date_compta[3:5] + date_compta[:2]
        n_piece_banque = f"AMEX-{cle_date_banque}"

        lignes_finales.append({
            "STE": STE_DEFAUT,
            "DATE": date_compta,
            "COMPTE": "512120",
            "Auxiliaire": "",
            "n°pièce": n_piece_banque,
            "OBJET": "Virement AMEX caisse → Banque",
            "D": "",
            "C": format_montant(total_net),
            "Journal": JOURNAUX["amex_caisse"],
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
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_amex_caisse.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export AMEX CAISSE : {sortie.name} ({len(lignes_finales)} écritures)")

    return sortie

# ==========================================================
# CLASSE HANDLER
# ==========================================================

class TraiterAmexCaisseHandler:
    """Handler pour traiter les fichiers AMEX caisse."""

    @staticmethod
    def traiter(fichier: Path) -> None:
        """Traite un fichier AMEX caisse."""
        traiter_amex_caisse(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """Vérifie si c'est un fichier AMEX caisse."""
        return detecteur_result.get("type") == "amex_caisse"

__all__ = ['TraiterAmexCaisseHandler', 'traiter_amex_caisse']
