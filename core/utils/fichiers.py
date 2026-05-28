# core/utils/fichiers.py
"""
Utilitaires pour la lecture et conversion de fichiers.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def lire_xlsx(chemin: Path, header: int = 0) -> Optional[pd.DataFrame]:
    """
    Lit un fichier XLSX de manière robuste.

    Args:
        chemin: Chemin du fichier
        header: Ligne d'en-tête (défaut: 0)

    Returns:
        DataFrame ou None si erreur
    """
    try:
        if not chemin.exists():
            logger.error(f"Fichier non trouvé: {chemin}")
            return None

        df = pd.read_excel(chemin, header=header, engine='openpyxl')
        logger.debug(f"Fichier lu: {chemin.name} ({len(df)} lignes)")
        return df

    except Exception as e:
        logger.error(f"Erreur lecture {chemin.name}: {e}")
        return None


def lire_csv(chemin: Path, header: int = 0, sep: str = ",") -> Optional[pd.DataFrame]:
    """
    Lit un fichier CSV de manière robuste.

    Args:
        chemin: Chemin du fichier
        header: Ligne d'en-tête (défaut: 0)
        sep: Séparateur (défaut: ",")

    Returns:
        DataFrame ou None si erreur
    """
    try:
        if not chemin.exists():
            logger.error(f"Fichier non trouvé: {chemin}")
            return None

        df = pd.read_csv(chemin, header=header, sep=sep)
        logger.debug(f"Fichier CSV lu: {chemin.name} ({len(df)} lignes)")
        return df

    except Exception as e:
        logger.error(f"Erreur lecture CSV {chemin.name}: {e}")
        return None


def convertir_xls_en_xlsx(chemin: Path) -> Optional[Path]:
    """
    Convertit un fichier XLS en XLSX.

    Args:
        chemin: Chemin du fichier XLS

    Returns:
        Chemin du fichier XLSX créé, ou None si erreur
    """
    try:
        if chemin.suffix.lower() != ".xls":
            logger.warning(f"Fichier n'est pas un XLS: {chemin}")
            return chemin

        df = pd.read_excel(chemin, engine='xlrd')
        chemin_xlsx = chemin.with_suffix('.xlsx')
        df.to_excel(chemin_xlsx, index=False, engine='openpyxl')

        logger.info(f"Conversion XLS→XLSX: {chemin.name} → {chemin_xlsx.name}")
        return chemin_xlsx

    except Exception as e:
        logger.error(f"Erreur conversion XLS: {e}")
        return None


__all__ = ["lire_xlsx", "lire_csv", "convertir_xls_en_xlsx"]
