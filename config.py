# config.py
import sys
import logging
from pathlib import Path

# ── Logger bootstrap ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger("config")

_log.debug("=== CHARGEMENT config.py ===")
_log.debug(f"sys.frozen     = {getattr(sys, 'frozen', False)}")
_log.debug(f"sys.executable = {sys.executable}")
_log.debug(f"__file__       = {__file__}")

# ── BASE_DIR ──────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

_log.debug(f"BASE_DIR = {BASE_DIR}")

# ── Chemins relatifs à BASE_DIR ───────────────────────────────────────────────
DOSSIER_BRUT   = BASE_DIR / "fichiers_brut"
DOSSIER_BACKUP = BASE_DIR / "backup"
DOSSIER_SORTIE = BASE_DIR / "sorties" / "fichiers_compta"

# Dossier dédié aux exports de justification internet
DOSSIER_JUSTIFICATION = BASE_DIR / "sorties" / "justification"

_log.debug(f"DOSSIER_BRUT          = {DOSSIER_BRUT}")
_log.debug(f"DOSSIER_BACKUP        = {DOSSIER_BACKUP}")
_log.debug(f"DOSSIER_SORTIE        = {DOSSIER_SORTIE}")
_log.debug(f"DOSSIER_JUSTIFICATION = {DOSSIER_JUSTIFICATION}")

# ── Création des dossiers ─────────────────────────────────────────────────────
for _d in [DOSSIER_BRUT, DOSSIER_BACKUP, DOSSIER_SORTIE, DOSSIER_JUSTIFICATION]:
    try:
        _d.mkdir(parents=True, exist_ok=True)
        _log.debug(f"Dossier OK : {_d}")
    except Exception as e:
        _log.critical(f"Impossible de créer {_d} : {e}")
        raise

# ── Fichier correspondance AMEX ───────────────────────────────────────────────
def trouver_correspondance_amex() -> Path:
    _log.debug("Recherche fichier correspondance_amex...")
    nom  = "correspondance_amex"
    exts = [".csv", ".xlsx", ".xls"]

    for dossier in [BASE_DIR, DOSSIER_SORTIE]:
        for ext in exts:
            candidat = dossier / f"{nom}{ext}"
            _log.debug(f"  Teste : {candidat}")
            if candidat.exists():
                _log.info(f"Correspondance AMEX trouvée : {candidat}")
                return candidat

    fallback = DOSSIER_SORTIE / f"{nom}.csv"
    _log.warning(f"Correspondance AMEX introuvable, création fichier vide : {fallback}")
    fallback.touch()
    return fallback

FICHIER_CORRESPONDANCE_AMEX = trouver_correspondance_amex()
_log.debug(f"FICHIER_CORRESPONDANCE_AMEX = {FICHIER_CORRESPONDANCE_AMEX}")

# ── Colonnes de sortie ────────────────────────────────────────────────────────
COLONNES_SORTIE = [
    "STE", "DATE", "COMPTE", "Auxiliaire",
    "n°pièce", "OBJET", "D", "C", "Journal", "Analytique",
]

# ── Helpers chemins ───────────────────────────────────────────────────────────
def chemin_sortie(fichier: str) -> Path:
    return DOSSIER_SORTIE / fichier

def chemin_brut(fichier: str) -> Path:
    return DOSSIER_BRUT / fichier

def chemin_backup(fichier: str) -> Path:
    return DOSSIER_BACKUP / fichier

def chemin_justification(fichier: str) -> Path:
    """Retourne un chemin dans le dossier d'export justification."""
    return DOSSIER_JUSTIFICATION / fichier

_log.debug("=== config.py chargé avec succès ===")
