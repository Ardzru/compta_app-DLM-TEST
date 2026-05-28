"""
Module 3 - Génération automatique des lignes kiosque
"""
from datetime import datetime, timedelta
from pathlib import Path
from modules.module_3.stock import alimenter_depuis_caisse
from modules.module_3.remises import get_historique, ajouter_remise
import logging
import json

logger = logging.getLogger(__name__)

# Fichier de suivi des jours traités
KIOSQUE_TRACKER = Path(__file__).parent.parent.parent / "data" / "kiosque_tracker.json"


def _charger_tracker() -> dict:
    """Charge le fichier de suivi des jours traités"""
    if KIOSQUE_TRACKER.exists():
        try:
            with open(KIOSQUE_TRACKER, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def _sauvegarder_tracker(tracker: dict) -> None:
    """Sauvegarde le fichier de suivi"""
    KIOSQUE_TRACKER.parent.mkdir(parents=True, exist_ok=True)
    with open(KIOSQUE_TRACKER, 'w', encoding='utf-8') as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)


def generer_ligne_kiosque_auto(date_str: str = None) -> bool:
    """
    Génère une ligne kiosque automatique pour le jour.

    Args:
        date_str: Date au format JJ/MM/AAAA (default: aujourd'hui)

    Returns:
        True si généré, False si déjà existant
    """
    if date_str is None:
        date_str = datetime.now().strftime("%d/%m/%Y")

    tracker = _charger_tracker()

    # Vérifie si déjà traité aujourd'hui
    if tracker.get("derniere_date") == date_str:
        logger.debug(f"✓ Kiosque auto déjà créé pour {date_str}")
        return False

    try:
        # Données par défaut (0€ pour les coupures)
        donnees = {
            'detail_especes': {},  # vide au départ
            'detail_cheques_vac_coupures': {},
            'detail_cheques': [],
            'ancv_connect': 0.0
        }

        alimenter_depuis_caisse('kiosque_auto', date_str, donnees)

        # Met à jour le tracker
        tracker["derniere_date"] = date_str
        tracker["nb_generees"] = tracker.get("nb_generees", 0) + 1
        _sauvegarder_tracker(tracker)

        logger.info(f"✅ Ligne kiosque AUTO créée pour {date_str}")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur génération kiosque auto: {e}", exc_info=True)
        return False


def reset_tracker_kiosque():
    """Réinitialise le tracker (pour test)"""
    KIOSQUE_TRACKER.unlink(missing_ok=True)
    logger.info("🔄 Tracker kiosque réinitialisé")
