"""
Base handler classes pour tous les modules.
"""

from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
from config import logger  # ✅ CHANGÉ CETTE LIGNE

# ==========================================================
# ENUMS
# ==========================================================

class TypeModele(Enum):
    """Types de modules."""
    MODULE_1 = "module_1"
    MODULE_2 = "module_2"
    MODULE_3 = "module_3"

class StatusResultat(Enum):
    """Status du résultat."""
    SUCCES = "succes"
    ERREUR = "erreur"
    AVERTISSEMENT = "avertissement"

# ==========================================================
# RESULTAT
# ==========================================================

@dataclass
class ResultatHandler:
    """Résultat du traitement d'un handler."""

    fichier: Path
    status: StatusResultat
    message: str
    nb_lignes_traitees: int = 0
    fichier_sortie: Optional[Path] = None
    erreur: Optional[str] = None
    donnees: Dict[str, Any] = field(default_factory=dict)
    temps_execution: float = 0.0

    def __post_init__(self):
        """Valide le résultat."""
        if self.status == StatusResultat.ERREUR and not self.erreur:
            self.erreur = self.message

# ==========================================================
# BASE HANDLER
# ==========================================================

class FileHandlerBase:
    """Classe de base pour tous les handlers."""

    nom: str = "BaseHandler"
    description: str = "Handler de base"
    type_module: TypeModele = TypeModele.MODULE_1

    def __init__(self):
        """Initialise le handler."""
        self._debut = None

    # ────────────────────────────────────────────────────────
    # TIMER
    # ────────────────────────────────────────────────────────

    def demarrer_timer(self) -> None:
        """Démarre le timer."""
        self._debut = datetime.now()

    def arreter_timer(self) -> float:
        """Arrête le timer et retourne les secondes."""
        if not self._debut:
            return 0.0
        delta = (datetime.now() - self._debut).total_seconds()
        return round(delta, 2)

    # ────────────────────────────────────────────────────────
    # LOGGING
    # ────────────────────────────────────────────────────────

    def log_info(self, msg: str) -> None:
        """Log info."""
        logger.info(f"[{self.nom}] {msg}")

    def log_debug(self, msg: str) -> None:
        """Log debug."""
        logger.debug(f"[{self.nom}] {msg}")

    def log_warning(self, msg: str) -> None:
        """Log warning."""
        logger.warning(f"[{self.nom}] {msg}")

    def log_error(self, msg: str) -> None:
        """Log error."""
        logger.error(f"[{self.nom}] {msg}")
