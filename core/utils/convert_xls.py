import pandas as pd
from pathlib import Path
import logging
import openpyxl

logger = logging.getLogger("compta")

def convertir_xls_en_xlsx(fichier: Path) -> Path:
    """
    Convertit un fichier .xls en .xlsx avec openpyxl (plus robuste).
    Si le fichier .xlsx existe déjà, il est retourné directement.

    Args:
        fichier (Path): Chemin du fichier .xls

    Returns:
        Path: Chemin du fichier .xlsx

    Raises:
        FileNotFoundError: Si le fichier source n'existe pas
        RuntimeError: Si la conversion échoue
    """

    fichier = Path(fichier)

    # ✅ Vérification que c'est bien un .xls
    if fichier.suffix.lower() != ".xls":
        logger.warning(f"convertir_xls_en_xlsx appelé sur un fichier non .xls : {fichier.name}")
        return fichier

    # ✅ Vérification que le fichier source existe
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier source introuvable : {fichier}")

    nouveau = fichier.with_suffix(".xlsx")

    # ✅ Déjà converti → on retourne directement
    if nouveau.exists():
        logger.debug(f"Fichier déjà converti, réutilisation : {nouveau.name}")
        return nouveau

    logger.info(f"Conversion XLS → XLSX : {fichier.name}")

    try:
        # ✅ Lecture avec xlrd (spécifique .xls)
        df = pd.read_excel(
            fichier,
            sheet_name=0,  # ← Lire la première feuille explicitement
            header=None,
            engine="xlrd",
            dtype=str  # ← Garder tout en string pour éviter les conversions
        )

        # ✅ Écriture avec openpyxl
        with pd.ExcelWriter(nouveau, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False, header=False)

        logger.info(f"✅ Conversion réussie : {nouveau.name}")

    except Exception as e:
        logger.error(f"❌ Échec conversion {fichier.name} : {e}")
        raise RuntimeError(f"Impossible de convertir {fichier.name} en xlsx : {e}") from e

    return nouveau

__all__ = ["convertir_xls_en_xlsx"]
