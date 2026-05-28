# modules/__init__.py

"""
Modules - Tous les packages de traitement
"""

from . import module_1
from . import module_2
from . import module_3

# ✅ Importe UNIQUEMENT les fonctions qui existent réellement
from .module_1.handlers import (
    traiter_alma,
    traiter_amex_caisse,
    traiter_amex_internet,
    traiter_ancv,
    traiter_avoirs,
    traiter_banque,
    traiter_kiosk_photo,
    traiter_planet,
    traiter_ta,
)

from .module_2.handlers import (
    traiter_alpilink,
    traiter_banque as traiter_banque_justif,
    traiter_compta,
)

__all__ = [
    # Modules
    "module_1",
    "module_2",
    "module_3",

    # Module 1 - Handlers de conversion
    "traiter_alma",
    "traiter_amex_caisse",
    "traiter_amex_internet",
    "traiter_ancv",
    "traiter_avoirs",
    "traiter_banque",
    "traiter_kiosk_photo",
    "traiter_planet",
    "traiter_ta",

    # Module 2 - Handlers de justification
    "traiter_alpilink",
    "traiter_banque_justif",
    "traiter_compta",
]
