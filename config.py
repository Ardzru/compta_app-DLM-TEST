"""
Configuration centrale de l'application.
"""

import sys
import logging
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# LOGGER BOOTSTRAP
# ══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger("config")

_log.debug("=== CHARGEMENT config.py ===")
_log.debug(f"sys.frozen     = {getattr(sys, 'frozen', False)}")
_log.debug(f"sys.executable = {sys.executable}")

# ══════════════════════════════════════════════════════════════════════════════
# BASE_DIR & CHEMINS
# ══════════════════════════════════════════════════════════════════════════════

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

_log.debug(f"BASE_DIR = {BASE_DIR}")

# Dossiers
DOSSIER_BRUT          = BASE_DIR / "fichiers_brut"
DOSSIER_BACKUP        = BASE_DIR / "backup"
DOSSIER_SORTIE        = BASE_DIR / "sorties" / "fichiers_compta"
DOSSIER_JUSTIFICATION = BASE_DIR / "sorties" / "justification"
DOSSIER_SAISIES       = BASE_DIR / "data" / "saisies"

# Créer les dossiers
for _d in [DOSSIER_BRUT, DOSSIER_BACKUP, DOSSIER_SORTIE, DOSSIER_JUSTIFICATION, DOSSIER_SAISIES]:
    try:
        _d.mkdir(parents=True, exist_ok=True)
        _log.debug(f"✓ Dossier : {_d}")
    except Exception as e:
        _log.critical(f"❌ Impossible de créer {_d} : {e}")
        raise

# ══════════════════════════════════════════════════════════════════════════════
# LOGGER FICHIER
# ══════════════════════════════════════════════════════════════════════════════

LOG_FILE = BASE_DIR / "traitement.log"

# Handler fichier
file_handler = logging.FileHandler(
    LOG_FILE,
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s",
                      datefmt="%d/%m/%Y %H:%M:%S")
)

# Logger principal
logger = logging.getLogger("compta")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Ajouter aussi un handler console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("[%(levelname)s] %(message)s")
)
logger.addHandler(console_handler)

_log.info(f"Logger fichier : {LOG_FILE}")

# ══════════════════════════════════════════════════════════════════════════════
# MOIS & CORRESPONDANCES
# ══════════════════════════════════════════════════════════════════════════════

CAISSES_MOIS_FR = {
    1:  "01_Janvier",
    2:  "02_Fevrier",
    3:  "03_Mars",
    4:  "04_Avril",
    5:  "05_Mai",
    6:  "06_Juin",
    7:  "07_Juillet",
    8:  "08_Aout",
    9:  "09_Septembre",
    10: "10_Octobre",
    11: "11_Novembre",
    12: "12_Decembre",
}

def trouver_correspondance_amex() -> Path:
    """Cherche le fichier de correspondance AMEX."""
    _log.debug("Recherche fichier correspondance_amex...")
    nom  = "correspondance_amex"
    exts = [".csv", ".xlsx", ".xls"]

    for dossier in [BASE_DIR, DOSSIER_SORTIE]:
        for ext in exts:
            candidat = dossier / f"{nom}{ext}"
            if candidat.exists():
                _log.info(f"✓ Correspondance AMEX trouvée : {candidat}")
                return candidat

    fallback = DOSSIER_SORTIE / f"{nom}.csv"
    _log.warning(f"Correspondance AMEX introuvable : {fallback}")
    fallback.touch()
    return fallback

FICHIER_CORRESPONDANCE_AMEX = trouver_correspondance_amex()

# ══════════════════════════════════════════════════════════════════════════════
# COLONNES DE SORTIE
# ══════════════════════════════════════════════════════════════════════════════

COLONNES_SORTIE = [
    "STE", "DATE", "COMPTE", "Auxiliaire",
    "n°pièce", "OBJET", "D", "C", "Journal", "Analytique",
]

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS CHEMINS
# ══════════════════════════════════════════════════════════════════════════════

def chemin_sortie(fichier: str) -> Path:
    return DOSSIER_SORTIE / fichier

def chemin_brut(fichier: str) -> Path:
    return DOSSIER_BRUT / fichier

def chemin_backup(fichier: str) -> Path:
    return DOSSIER_BACKUP / fichier

def chemin_justification(fichier: str) -> Path:
    return DOSSIER_JUSTIFICATION / fichier

def chemin_saisie(fichier: str) -> Path:
    return DOSSIER_SAISIES / fichier

# ══════════════════════════════════════════════════════════════════════════════
# FIN
# ══════════════════════════════════════════════════════════════════════════════

_log.debug("=== config.py CHARGÉ AVEC SUCCÈS ===")
