# modules/module_1/handlers/__init__.py

"""
Module des handlers Module 1 (transformation fichiers bruts → CSV compta)
"""

# ✅ Importe UNIQUEMENT les fonctions, pas les classes
from .traiter_alma import traiter_alma
from .traiter_ancv import traiter_ancv
from .traiter_amex_caisse import traiter_amex_caisse
from .traiter_amex_internet import traiter_amex_internet
from .traiter_banque import traiter_banque
from .traiter_ta import traiter_ta
from .traiter_avoirs import traiter_avoirs
from .traiter_kiosk_photo import traiter_kiosk_photo
from .traiter_planet import traiter_planet

__all__ = [
    'traiter_alma',
    'traiter_ancv',
    'traiter_amex_caisse',
    'traiter_amex_internet',
    'traiter_banque',
    'traiter_ta',
    'traiter_avoirs',
    'traiter_kiosk_photo',
    'traiter_planet',
]
