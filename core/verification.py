# core/verification.py

import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def calculer_total_pieces(detail_especes):
    """
    Calcule le total des pièces (0.01 à 2€)

    Args:
        detail_especes: dict avec structure {'2': {'quantite': 1, 'montant': 2}, ...}

    Returns:
        float: montant total des pièces
    """
    coupures_pieces = ["2", "1", "0.5", "0.2", "0.1", "0.05", "0.02", "0.01"]

    total = 0.0
    for coupure in coupures_pieces:
        if coupure in detail_especes:
            montant = float(detail_especes[coupure].get('montant', 0) or 0)
            total += montant
            logger.debug(f"  Pièce {coupure}€: {montant}€ → total: {total}€")

    logger.info(f"✅ Total pièces calculé: {total}€")
    return total


def calculer_total_billets(detail_especes):
    """
    Calcule le total des billets (5€ à 500€)

    Args:
        detail_especes: dict avec structure

    Returns:
        float: montant total des billets
    """
    coupures_billets = ["500", "200", "100", "50", "20", "10", "5"]

    total = 0.0
    for coupure in coupures_billets:
        if coupure in detail_especes:
            montant = float(detail_especes[coupure].get('montant', 0) or 0)
            total += montant
            logger.debug(f"  Billet {coupure}€: {montant}€ → total: {total}€")

    logger.info(f"✅ Total billets calculé: {total}€")
    return total


def charger_verification(date_str):
    """
    Charge les données de vérification pour une date donnée

    Args:
        date_str: Date au format "JJ/MM/AAAA"

    Returns:
        dict avec structure: {
            'caisses_verif': {
                'Caisse 1': {'total_billets': X, 'total_pieces': Y},
                'Caisse 2': {...},
                ...
            }
        }
    """
    try:
        fichier_verif = Path(f"data/verification_{date_str.replace('/', '-')}.json")

        if not fichier_verif.exists():
            logger.warning(f"Fichier de vérification non trouvé : {fichier_verif}")
            return None

        with open(fichier_verif, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Vérification chargée : {fichier_verif}")
        return data

    except Exception as e:
        logger.error(f"Erreur lors du chargement de la vérification : {e}")
        return None


def sauvegarder_verification(date_str, donnees_verif):
    """
    Sauvegarde les données de vérification

    Args:
        date_str: Date au format "JJ/MM/AAAA"
        donnees_verif: dict avec les données vérifiées
    """
    try:
        fichier_verif = Path(f"data/verification_{date_str.replace('/', '-')}.json")
        fichier_verif.parent.mkdir(parents=True, exist_ok=True)

        with open(fichier_verif, 'w', encoding='utf-8') as f:
            json.dump(donnees_verif, f, indent=2, ensure_ascii=False)

        logger.info(f"Vérification sauvegardée : {fichier_verif}")

    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la vérification : {e}")


def recalculer_totaux_verification(date_str):
    """
    ✅ RECALCULE LES TOTAUX DE TOUTES LES CAISSES D'UN JOUR
    À utiliser après chaque modification
    """
    verif_data = charger_verification(date_str)

    if not verif_data or 'caisses_verif' not in verif_data:
        logger.warning(f"Pas de données à recalculer pour {date_str}")
        return

    logger.info(f"🔄 RECALCUL DES TOTAUX POUR {date_str}")

    caisses_verif = verif_data['caisses_verif']

    for num_caisse, caisse_data in caisses_verif.items():
        # Récupérer le detail_especes depuis tous_modes
        tous_modes = caisse_data.get('tous_modes', {})
        detail_especes = tous_modes.get('detail_especes', {})

        if detail_especes:
            # Recalculer
            total_billets = calculer_total_billets(detail_especes)
            total_pieces = calculer_total_pieces(detail_especes)

            # Mettre à jour
            caisse_data['total_billets'] = total_billets
            caisse_data['total_pieces'] = total_pieces
            caisse_data['total_especes'] = total_billets + total_pieces

            logger.info(
                f"  {num_caisse}: {total_billets}€ billets + {total_pieces}€ pièces = {total_billets + total_pieces}€")

    # Sauvegarder
    sauvegarder_verification(date_str, verif_data)
    logger.info(f"✅ TOTAUX RECALCULÉS ET SAUVEGARDÉS")
