"""
Module 3 UI - Interface utilisateur pour caisses, stocks et remises.
"""

from .caisses_ui import AppCaisses
from .detail_caisse import DetailCaissePopup
from .remise_ui import RemiseUI

__all__ = [
    "AppCaisses",
    "DetailCaissePopup",
    "RemiseUI",
]
