# modules/module_3/handlers/__init__.py
"""
Handlers Module 3 - Caisses, Stock, Remises
Opérations DB + Utilitaires
"""

# Import des DB handlers
from . import db_caisses
from . import db_caisses_especes
from . import db_caisses_lignes
from . import db_stock
from . import db_remises

__all__ = [
    "db_caisses",
    "db_caisses_especes",
    "db_caisses_lignes",
    "db_stock",
    "db_remises",
]
