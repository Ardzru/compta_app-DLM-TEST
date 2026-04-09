# core/moniteur_schema.py

import pandas as pd
from logger import logger

# ==========================================================
# SCHÉMAS ATTENDUS PAR TYPE DE FICHIER
# ==========================================================
SCHEMAS = {
    "banque": {
        "nb_colonnes_min": 9,
        "description": "Fichier bancaire CSV (TRANSACTION / CAPTURED)",
    },
    "amex": {
        "nb_colonnes_min": 27,
        "description": "Fichier AMEX Excel (SOC/ROC)",
    },
    "avoirs": {
        "nb_colonnes_min": 5,
        "description": "Fichier avoirs Excel",
    },
    "ancv": {
        "nb_colonnes_min": 4,
        "description": "Fichier ANCV CSV",
    },
}

# ==========================================================
# FONCTION PRINCIPALE
# ==========================================================

def comparer_schema(df: pd.DataFrame, type_fichier: str) -> bool:
    """
    Vérifie que le DataFrame respecte le schéma minimal attendu.

    Retourne True si OK, False si anomalie (sans bloquer le traitement).
    """
    schema = SCHEMAS.get(type_fichier)

    if schema is None:
        logger.warning(f"[SCHEMA] Type inconnu : {type_fichier!r} → vérification ignorée")
        return True

    nb_col = df.shape[1]
    nb_col_min = schema["nb_colonnes_min"]

    if nb_col < nb_col_min:
        logger.warning(
            f"[SCHEMA] {type_fichier.upper()} : "
            f"{nb_col} colonnes trouvées, {nb_col_min} attendues minimum "
            f"→ fichier peut-être mal formé"
        )
        return False

    logger.debug(
        f"[SCHEMA] {type_fichier.upper()} OK "
        f"({nb_col} colonnes ✓)"
    )
    return True
