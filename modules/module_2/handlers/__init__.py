# modules/module_2/handlers/__init__.py
"""Handlers Module 2 - Comptabilité & Intégration"""

from core.detecteur import est_alpilink, est_banque_internet, est_compta_internet

from .alpilink_handler import traiter_alpilink, charger_alpilink, extraire_commandes_alpilink
from .banque_handler import traiter_banque, charger_banque, extraire_commandes
from .compta_handler import traiter_compta, charger_compta, extraire_commandes as extraire_commandes_compta

__all__ = [
    "est_alpilink",
    "est_banque_internet",
    "est_compta_internet",
    "traiter_alpilink",
    "traiter_banque",
    "traiter_compta",
    "charger_alpilink",
    "charger_banque",
    "charger_compta",
    "extraire_commandes",
    "extraire_commandes_compta",
    "extraire_commandes_alpilink",
]
