"""
Module 2 : Traitement TA pour justification compte internet
"""

import re
import pandas as pd
from pathlib import Path
from typing import Optional
from collections import defaultdict

from config import DOSSIER_SORTIE, logger

from core.utils.montant import to_float, format_montant
from core.utils.date import formater_date
from core.utils.colonnes import STE_DEFAUT, COLONNES_SORTIE
from core.utils.constantes import (
    COMPTE_TRANSIT,
    JOURNAUX,
)
from core.moniteur_schema import comparer_schema

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotTAFileError(Exception):
    """Levée si aucune ligne TA exploitable n'est trouvée."""
    pass

# ==========================================================
# CONSTANTES COLONNES TA (SPÉCIFIQUES AU MODULE)
# ==========================================================

TA_COLONNES = {
    "num_commande": "Numéro de commande",
    "date": "Date",
    "caisse": "Caisse",
    "libelle": "Libellé",
    "montant_ventes": "Montant ventes",
    "montant_annulations": "Montant annulations",
}

TA_CAISSES_AUTORISEES = ["72", "73", "77"]

TA_LIBELLES_VENTES = ["VENTE", "VENTE NETTE"]
TA_LIBELLES_ANNULATIONS = ["ANNULATION", "RETOUR"]

# ==========================================================
# UTILITAIRES PRIVÉS
# ==========================================================

def _nettoyer_commande(val) -> Optional[str]:
    """
    Extrait et normalise le numéro de commande.
    - Conserve uniquement les chiffres
    - Nécessite au moins 8 chiffres
    - Retourne les 8 premiers chiffres
    """
    if pd.isna(val):
        return None
    chiffres = re.findall(r"\d", str(val))
    if len(chiffres) < 8:
        return None
    return "".join(chiffres[:8])

def _verifier_colonnes(df: pd.DataFrame, fichier: Path) -> None:
    """Vérifie que les colonnes attendues sont présentes."""
    colonnes_requises = list(TA_COLONNES.values())
    manquantes = [c for c in colonnes_requises if c not in df.columns]
    if manquantes:
        raise ValueError(
            f"Colonnes manquantes dans {fichier.name} : {manquantes}\n"
            f"Colonnes trouvées : {list(df.columns)}"
        )

# ==========================================================
# FONCTION PRINCIPALE
# ==========================================================

def traiter_ta(fichier: Path) -> Optional[Path]:
    """
    Traite un fichier TA (billetterie / caisse) et génère
    les écritures comptables correspondantes pour justification.

    Règles métier :
    - Seules les caisses 72, 73, 77 sont traitées
    - Ventes → Débit COMPTE_TRANSIT
    - Annulations → Crédit COMPTE_TRANSIT
    - Contrepartie par caisse (diff ventes - annulations)

    Args:
        fichier: Path du fichier TA

    Returns:
        Path: Chemin du fichier généré ou None
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier TA introuvable : {fichier}")

    logger.info(f"Traitement TA : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture + validation schéma
    # ----------------------------------------------------------
    df = pd.read_excel(fichier)

    if df.empty:
        logger.error(f"Fichier vide : {fichier.name}")
        return None

    _verifier_colonnes(df, fichier)
    logger.info(f"Colonnes trouvées : {list(df.columns)}")

    # ----------------------------------------------------------
    # 2. Parcours des lignes
    # ----------------------------------------------------------
    commandes: dict = {}  # { num_commande: {"date": str, "D": float, "C": float, "caisse": str, "libelle": str} }
    nb_ignores = 0

    for idx, row in df.iterrows():
        try:
            # Nettoyage commande
            commande_raw = row[TA_COLONNES["num_commande"]]
            commande_num = _nettoyer_commande(commande_raw)

            if not commande_num:
                logger.debug(f"Ligne {idx} ignorée : commande invalide {commande_raw!r}")
                nb_ignores += 1
                continue

            # Extraction données
            date_str = str(row[TA_COLONNES["date"]]).strip()
            date_compta = formater_date(date_str)
            if not date_compta:
                logger.debug(f"Ligne {idx} ignorée : date invalide {date_str!r}")
                nb_ignores += 1
                continue

            caisse = str(row[TA_COLONNES["caisse"]]).strip()
            if caisse not in TA_CAISSES_AUTORISEES:
                logger.debug(f"Ligne {idx} ignorée : caisse non autorisée {caisse}")
                nb_ignores += 1
                continue

            libelle = str(row[TA_COLONNES["libelle"]]).strip().upper()
            montant_ventes = to_float(row[TA_COLONNES["montant_ventes"]])
            montant_annuls = to_float(row[TA_COLONNES["montant_annulations"]])

            # Initialiser si première occurrence
            if commande_num not in commandes:
                commandes[commande_num] = {
                    "date": date_compta,
                    "D": 0.0,
                    "C": 0.0,
                    "caisse": caisse,
                    "libelle": libelle,
                }

            # Ajouter montants
            if any(v in libelle for v in TA_LIBELLES_VENTES):
                commandes[commande_num]["D"] += montant_ventes
            elif any(a in libelle for a in TA_LIBELLES_ANNULATIONS):
                commandes[commande_num]["C"] += montant_annuls

        except Exception as e:
            logger.warning(f"Ligne {idx} ignorée : {str(e)}")
            nb_ignores += 1
            continue

    if not commandes:
        logger.error(f"Aucune ligne exploitable trouvée dans {fichier.name}")
        raise NotTAFileError(f"Aucune ligne exploitable : {fichier.name}")

    logger.info(f"Lignes traitées : {len(commandes)} commandes, {nb_ignores} ignorées")

    # ----------------------------------------------------------
    # 3. Construction des écritures
    # ----------------------------------------------------------
    lignes_finales = []
    compte_base = COMPTE_TRANSIT[:-2]  # "580010" (sans "DS5")

    for commande_num, data in sorted(commandes.items()):
        date_compta = data["date"]
        D = round(data["D"], 2)
        C = round(data["C"], 2)
        caisse = data["caisse"]

        # Ligne 1 : Compte transit
        if D != 0.0:
            lignes_finales.append({
                "STE": STE_DEFAUT,
                "DATE": date_compta,
                "COMPTE": COMPTE_TRANSIT,
                "Auxiliaire": "",
                "n°pièce": f"TA-{commande_num}",
                "OBJET": f"TA {data['libelle']} - Commande {commande_num}",
                "D": format_montant(D),
                "C": "",
                "Journal": JOURNAUX["ta"],
                "Analytique": "",
            })

        # Ligne 2 : Contrepartie par caisse
        caisse_compte = f"{compte_base}{caisse[-2:]}"
        solde = round(D - C, 2)

        if solde != 0.0:
            lignes_finales.append({
                "STE": STE_DEFAUT,
                "DATE": date_compta,
                "COMPTE": caisse_compte,
                "Auxiliaire": f"CAISSE {caisse}",
                "n°pièce": f"TA-{commande_num}",
                "OBJET": f"Contrepartie caisse {caisse}",
                "D": "" if solde > 0 else format_montant(abs(solde)),
                "C": format_montant(solde) if solde > 0 else "",
                "Journal": JOURNAUX["ta"],
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
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_ta.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export TA : {sortie.name} ({len(lignes_finales)} écritures)")

    return sortie

# ==========================================================
# CLASSE HANDLER
# ==========================================================

class TraiterTaHandler:
    """Handler pour traiter les fichiers TA."""

    nom = "TraiterTaHandler"
    description = "Traitement des fichiers TA (billetterie/caisse)"

    def __init__(self):
        """Initialise le handler TA."""
        pass

    def traiter(self, fichier: Path) -> Optional[Path]:
        """
        Traite un fichier TA.

        Args:
            fichier: Path du fichier à traiter

        Returns:
            Path du fichier généré ou None
        """
        return traiter_ta(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """
        Vérifie si c'est un fichier TA.

        Args:
            detecteur_result: Résultat du détecteur

        Returns:
            True si c'est un TA, False sinon
        """
        return detecteur_result.get("type") == "ta"


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = ['TraiterTaHandler', 'traiter_ta', 'NotTAFileError']
