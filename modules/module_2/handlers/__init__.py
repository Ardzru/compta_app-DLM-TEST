# modules/module_2/handlers/__init__.py
"""Handlers Module 2 - Comptabilité & Intégration"""

from .alpilink_handler import traiter_alpilink
from .banque_handler import traiter_banque
from .compta_handler import traiter_compta

__all__ = [
    "traiter_alpilink",
    "traiter_banque",
    "traiter_compta",
]
