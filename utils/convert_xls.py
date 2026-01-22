import pandas as pd
from pathlib import Path
from logger import logger


def convertir_xls_en_xlsx(fichier: Path) -> Path:
    """
    Convertit un fichier .xls en .xlsx et retourne le nouveau chemin.
    """
    nouveau = fichier.with_suffix(".xlsx")

    if nouveau.exists():
        return nouveau

    logger.info(f"Conversion XLS → XLSX : {fichier.name}")

    df = pd.read_excel(fichier, header=None)
    df.to_excel(nouveau, index=False, header=False)

    return nouveau
