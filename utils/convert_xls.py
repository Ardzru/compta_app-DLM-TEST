import pandas as pd
from pathlib import Path
from logger import logger


def convertir_xls_en_xlsx(fichier: Path) -> Path:
    """
    Convertit un fichier .xls en .xlsx et retourne le nouveau chemin.
    Si le fichier .xlsx existe déjà, il est retourné directement sans reconversion.
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
        # ✅ Engine explicite pour la lecture .xls
        df = pd.read_excel(fichier, header=None, engine="xlrd")

        # ✅ Engine explicite pour l'écriture .xlsx
        df.to_excel(nouveau, index=False, header=False, engine="openpyxl")

        logger.info(f"Conversion réussie : {nouveau.name}")

    except Exception as e:
        logger.error(f"Échec conversion {fichier.name} : {e}")
        raise RuntimeError(f"Impossible de convertir {fichier.name} en xlsx : {e}") from e

    return nouveau
