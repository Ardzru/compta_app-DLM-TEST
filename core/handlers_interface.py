"""
Interface abstraite pour les handlers.
Permet à core/dispatcher.py d'appeler les handlers sans importer directement depuis modules/.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

class Module1HandlerInterface(ABC):
    """
    Interface abstraite pour les handlers du Module 1.
    Tous les handlers du Module 1 doivent implémenter cette interface.
    """

    @abstractmethod
    def traiter(self, fichier: Path) -> Any:
        """
        Traite un fichier et retourne le résultat.

        Args:
            fichier (Path): Chemin vers le fichier à traiter.

        Returns:
            Any: Résultat du traitement (fichier de sortie, dict, etc.).
        """
        pass

class Module2HandlerInterface(ABC):
    """
    Interface abstraite pour les handlers du Module 2.
    Tous les handlers du Module 2 doivent implémenter cette interface.
    """

    @abstractmethod
    def traiter(self, fichier: Path) -> Any:
        """
        Traite un fichier et retourne le résultat.

        Args:
            fichier (Path): Chemin vers le fichier à traiter.

        Returns:
            Any: Résultat du traitement (fichier de sortie, dict, etc.).
        """
        pass
