"""
Module 3 - Generation automatique des lignes kiosque.
"""

import json
from pathlib import Path
from datetime import datetime, date
from config import logger
from .lecteur_caisse import (
    trouver_dossier_jour,
    lister_caisses,
    lire_montants_caisse,
    extraire_numero_caisse,
)
from .stock import alimenter_depuis_caisse

KIOSQUE_TRACKER = Path("data/kiosque_tracker.json")


def generer_ligne_kiosque_auto(date_caisse: date = None) -> bool:
    """
    Genere automatiquement une ligne kiosque pour le jour.
    Cree une ligne d'alimentation stock depuis les caisses du jour.

    Args:
        date_caisse: datetime.date (defaut = aujourd'hui)

    Returns:
        True si cree, False si deja existant
    """
    if date_caisse is None:
        date_caisse = date.today()

    jour_str = date_caisse.strftime("%Y-%m-%d")

    # Verifier si deja traite
    tracker = _charger_tracker()
    if jour_str in tracker:
        logger.debug(f"[MODULE3][KIOSQUE] {jour_str} deja traite")
        return False

    # Chercher les caisses du jour
    dossier_jour = trouver_dossier_jour(date_caisse)
    if not dossier_jour:
        logger.warning(f"[MODULE3][KIOSQUE] Aucun dossier pour {jour_str}")
        return False

    fichiers_caisses = lister_caisses(dossier_jour)

    # Alimenter stock pour chaque caisse
    for chemin_caisse in fichiers_caisses:
        numero = extraire_numero_caisse(chemin_caisse)
        montants = lire_montants_caisse(chemin_caisse)

        alimenter_depuis_caisse(date_caisse, numero, montants.get("montants", {}))

    # Marquer comme traite
    _marquer_traite(jour_str)

    logger.info(f"[MODULE3][KIOSQUE] Ligne kiosque creee pour {jour_str}")
    return True


def _charger_tracker() -> dict:
    """Charge le tracker des jours traites."""
    if KIOSQUE_TRACKER.exists():
        try:
            return json.loads(KIOSQUE_TRACKER.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _marquer_traite(jour_str: str):
    """Marque un jour comme traite."""
    KIOSQUE_TRACKER.parent.mkdir(exist_ok=True)
    tracker = _charger_tracker()
    tracker[jour_str] = datetime.now().isoformat()

    try:
        KIOSQUE_TRACKER.write_text(
            json.dumps(tracker, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as exc:
        logger.error(f"[MODULE3][KIOSQUE] Erreur tracker: {exc}")


__all__ = [
    "generer_ligne_kiosque_auto",
]
