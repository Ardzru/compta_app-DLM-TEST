# core/moniteur_schema.py

import pandas as pd
from config import logger

# ==========================================================
# SCHÉMAS ATTENDUS PAR TYPE DE FICHIER
# ==========================================================
SCHEMAS = {
    # -------------------------------------------------------------------------
    # Module 1 - transformations validées
    # -------------------------------------------------------------------------
    "kiosk_photo": {
        "nb_colonnes_min": 3,
        "description": "Kiosk photo : dateheure / montant / vendeur",
    },
    "avoirs": {
        "nb_colonnes_min": 11,
        "description": "Fichier avoirs Excel",
    },
    "amex_caisse": {
        "nb_colonnes_min": 27,
        "description": "AMEX Caisse Excel SOC/ROC",
    },
    "amex_internet": {
        "nb_colonnes_min": 15,
        "description": "AMEX Internet Excel",
    },
    "planet": {
        "nb_colonnes_min": 10,
        "description": "Planet / DCC Statement Excel",
    },
    "alma": {
        "nb_colonnes_min": 6,
        "description": "ALMA Payments Excel",
    },
    "ta": {
        "nb_colonnes_min": 5,
        "description": "TA / Trésorier Excel",
    },

    # -------------------------------------------------------------------------
    # Module 1 - encore à corriger / surveiller
    # -------------------------------------------------------------------------
    "ancv": {
        "nb_colonnes_min": 4,
        "description": "Fichier ANCV CSV",
    },

    # -------------------------------------------------------------------------
    # Banque laissée volontairement pour plus tard
    # -------------------------------------------------------------------------
    "banque": {
        "nb_colonnes_min": 9,
        "description": "Fichier bancaire CSV ou rapprochement - laissé pour traitement ultérieur",
    },

    # -------------------------------------------------------------------------
    # Compatibilité anciens noms
    # -------------------------------------------------------------------------
    "amex": {
        "nb_colonnes_min": 27,
        "description": "Ancien alias AMEX Excel",
    },
}

# ==========================================================
# FONCTION PRINCIPALE
# ==========================================================

def comparer_schema(df: pd.DataFrame, type_fichier: str) -> bool:
    """
    Vérifie que le DataFrame respecte le schéma minimal attendu.

    Important :
    - Cette fonction ne bloque jamais le traitement.
    - Elle sert uniquement à produire des logs utiles.
    - Les types Module 1 validés ne doivent plus générer de faux WARNING.
    """
    schema = SCHEMAS.get(type_fichier)

    if schema is None:
        logger.debug(
            f"[SCHEMA] Type non référencé : {type_fichier!r} "
            f"→ vérification ignorée sans bloquer"
        )
        return True

    try:
        nb_col = df.shape[1]
    except Exception as e:
        logger.warning(
            f"[SCHEMA] Impossible de lire le nombre de colonnes pour "
            f"{type_fichier!r} : {e}"
        )
        return True

    nb_col_min = schema["nb_colonnes_min"]
    description = schema.get("description", type_fichier)

    if nb_col < nb_col_min:
        logger.warning(
            f"[SCHEMA] {type_fichier.upper()} : "
            f"{nb_col} colonnes trouvées, {nb_col_min} attendues minimum "
            f"({description}) → fichier peut-être mal formé"
        )
        return False

    logger.debug(
        f"[SCHEMA] {type_fichier.upper()} OK "
        f"({nb_col} colonnes, minimum {nb_col_min}) - {description}"
    )
    return True

