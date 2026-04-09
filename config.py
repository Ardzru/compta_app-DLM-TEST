from pathlib import Path

# Dossier du projet (portable)
BASE_DIR = Path(__file__).resolve().parent

# Dossier des fichiers bruts
DOSSIER_BRUT = BASE_DIR / "fichiers_brut"

# Dossier de backup
DOSSIER_BACKUP = BASE_DIR / "backup"

# Dossier de sortie (CSV compta)
DOSSIER_SORTIE = BASE_DIR / "sorties" / "fichiers_compta"

# Fichier de correspondance AMEX
FICHIER_CORRESPONDANCE_AMEX = BASE_DIR / "correspondance_amex.csv"

# Création des dossiers si besoin
DOSSIER_BRUT.mkdir(exist_ok=True)
DOSSIER_BACKUP.mkdir(exist_ok=True)
DOSSIER_SORTIE.mkdir(exist_ok=True)
