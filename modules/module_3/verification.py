# modules/module_3/verification.py
"""
Gestion des vérifications de caisses journalières.
Charge/sauvegarde les données de vérification en JSON.
"""

import json
from pathlib import Path
from config import logger
from core.utils.montant import to_float, format_montant
from core.utils.colonnes import COUPURES_BILLETS, COUPURES_PIECES

# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES PRIVÉS
# ══════════════════════════════════════════════════════════════════════════════

def _charger_verif(fichier_path: Path) -> dict:
    """Charge un fichier de vérification JSON."""
    try:
        if fichier_path.exists():
            data = json.loads(fichier_path.read_text(encoding="utf-8"))
            return data
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur JSON dans {fichier_path.name}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erreur lecture {fichier_path.name}: {e}")
        return None


def _sauvegarder_verif(fichier_path: Path, data: dict) -> bool:
    """Sauvegarde un fichier de vérification JSON."""
    try:
        fichier_path.parent.mkdir(parents=True, exist_ok=True)
        fichier_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.debug(f"✅ Vérification sauvegardée : {fichier_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde {fichier_path.name}: {e}")
        return False

# ══════════════════════════════════════════════════════════════════════════════
# CALCUL DES TOTAUX
# ══════════════════════════════════════════════════════════════════════════════

def calculer_total_pieces(detail_especes: dict) -> float:
    """
    Calcule le total des pièces (0.01 à 2€)

    Args:
        detail_especes: dict avec structure {'2': {'montant': 2}, ...}

    Returns:
        float: montant total des pièces

    Exemple:
        calculer_total_pieces({'0.5': {'montant': 1.5}, '0.2': {'montant': 0.4}})
        → 1.9
    """
    total = 0.0
    for coupure in COUPURES_PIECES:
        if coupure in detail_especes:
            montant = to_float(detail_especes[coupure].get('montant', 0))
            total += montant
            logger.debug(f"  Pièce {coupure}€: {format_montant(montant)}€")

    total = round(total, 2)
    logger.info(f"✅ Total pièces : {format_montant(total)}€")
    return total


def calculer_total_billets(detail_especes: dict) -> float:
    """
    Calcule le total des billets (5€ à 500€)

    Args:
        detail_especes: dict avec structure {'500': {'montant': 1000}, ...}

    Returns:
        float: montant total des billets

    Exemple:
        calculer_total_billets({'100': {'montant': 300}, '50': {'montant': 150}})
        → 450.0
    """
    total = 0.0
    for coupure in COUPURES_BILLETS:
        if coupure in detail_especes:
            montant = to_float(detail_especes[coupure].get('montant', 0))
            total += montant
            logger.debug(f"  Billet {coupure}€: {format_montant(montant)}€")

    total = round(total, 2)
    logger.info(f"✅ Total billets : {format_montant(total)}€")
    return total

# ══════════════════════════════════════════════════════════════════════════════
# GESTION FICHIERS VÉRIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def charger_verification(date_str: str) -> dict:
    """
    Charge les données de vérification pour une date donnée

    Args:
        date_str: Date au format "JJ/MM/AAAA" ou "JJ-MM-AAAA"

    Returns:
        dict avec structure: {
            'caisses_verif': {
                'Caisse 1': {'total_billets': X, 'total_pieces': Y, ...},
                'Caisse 2': {...},
                ...
            }
        }
        OU None si le fichier n'existe pas

    Exemple:
        data = charger_verification("20/05/2026")
        → {'caisses_verif': {'Caisse 1': {...}}}
    """
    # Normaliser la date
    date_fmt = date_str.replace('/', '-')
    fichier_verif = Path(f"data/verification_{date_fmt}.json")

    logger.debug(f"Chargement vérification : {fichier_verif}")

    data = _charger_verif(fichier_verif)

    if data:
        logger.info(f"✅ Vérification chargée : {len(data.get('caisses_verif', {}))} caisses")
    else:
        logger.warning(f"⚠️ Vérification non trouvée : {fichier_verif}")

    return data


def sauvegarder_verification(date_str: str, donnees_verif: dict) -> bool:
    """
    Sauvegarde les données de vérification

    Args:
        date_str: Date au format "JJ/MM/AAAA" ou "JJ-MM-AAAA"
        donnees_verif: dict avec les données vérifiées

    Returns:
        bool: True si succès, False sinon

    Exemple:
        data = {'caisses_verif': {'Caisse 1': {'total_billets': 1000}}}
        sauvegarder_verification("20/05/2026", data)
        → True
    """
    date_fmt = date_str.replace('/', '-')
    fichier_verif = Path(f"data/verification_{date_fmt}.json")

    if _sauvegarder_verif(fichier_verif, donnees_verif):
        logger.info(f"✅ Vérification sauvegardée : {fichier_verif}")
        return True
    return False


def recalculer_totaux_verification(date_str: str) -> bool:
    """
    ✅ RECALCULE LES TOTAUX DE TOUTES LES CAISSES D'UN JOUR
    À utiliser après chaque modification de caisse

    Args:
        date_str: Date au format "JJ/MM/AAAA"

    Returns:
        bool: True si succès, False sinon

    Exemple:
        recalculer_totaux_verification("20/05/2026")
        → True (et logs détaillés)
    """
    verif_data = charger_verification(date_str)

    if not verif_data or 'caisses_verif' not in verif_data:
        logger.warning(f"⚠️ Pas de données à recalculer pour {date_str}")
        return False

    logger.info(f"🔄 RECALCUL DES TOTAUX POUR {date_str}")

    caisses_verif = verif_data['caisses_verif']
    nb_recalcules = 0

    for num_caisse, caisse_data in caisses_verif.items():
        # Récupérer le detail_especes depuis tous_modes
        tous_modes = caisse_data.get('tous_modes', {})
        detail_especes = tous_modes.get('detail_especes', {})

        if not detail_especes:
            logger.debug(f"  {num_caisse} : pas de détail espèces, ignorée")
            continue

        # Recalculer
        total_billets = calculer_total_billets(detail_especes)
        total_pieces = calculer_total_pieces(detail_especes)
        total_especes = round(total_billets + total_pieces, 2)

        # Mettre à jour
        caisse_data['total_billets'] = total_billets
        caisse_data['total_pieces'] = total_pieces
        caisse_data['total_especes'] = total_especes
        nb_recalcules += 1

        logger.info(
            f"  {num_caisse}: "
            f"{format_montant(total_billets)}€ billets + "
            f"{format_montant(total_pieces)}€ pièces = "
            f"{format_montant(total_especes)}€"
        )

    # Sauvegarder
    success = sauvegarder_verification(date_str, verif_data)
    if success:
        logger.info(f"✅ {nb_recalcules} CAISSE(S) RECALCULÉE(S) ET SAUVEGARDÉE(S)")
    return success
