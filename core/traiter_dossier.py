import sys
from pathlib import Path
from datetime import date
import shutil

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.dispatcher import traiter_fichier
from logger import logger

DOSSIER_FICHIERS = Path("fichiers_brut")
ARCHIVE_BASE = Path("archive")
LOCK_FILE = Path("traitement.lock")


def lancer_traitement():
    if LOCK_FILE.exists():
        logger.warning("Traitement déjà en cours — abandon")
        return

    LOCK_FILE.touch()

    succes = 0
    erreurs = 0

    try:
        logger.info("=== DÉBUT DU TRAITEMENT ===")

        archive_jour = ARCHIVE_BASE / date.today().isoformat()
        archive_jour.mkdir(parents=True, exist_ok=True)

        for fichier in DOSSIER_FICHIERS.iterdir():
            if not fichier.is_file():
                continue

            try:
                # 🔁 Traitement
                traite = traiter_fichier(fichier)

                if traite:
                    succes += 1

                    # 📦 Archivage du fichier original
                    if fichier.exists():
                        shutil.move(str(fichier), archive_jour / fichier.name)
                        logger.info(f"Fichier archivé : {fichier.name}")

                    # 🧹 Suppression du fichier converti (.xlsx temporaire)
                    fichier_converti = fichier.with_suffix(".xlsx")
                    if fichier.suffix.lower() == ".xls" and fichier_converti.exists():
                        fichier_converti.unlink()
                        logger.info(f"Fichier temporaire supprimé : {fichier_converti.name}")

                else:
                    logger.warning(f"Fichier ignoré : {fichier.name}")

            except Exception:
                erreurs += 1
                logger.exception(f"Erreur sur {fichier.name}")

        logger.info("=== FIN DU TRAITEMENT ===")
        logger.info(f"Succès : {succes}")
        logger.info(f"Erreurs : {erreurs}")

    finally:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()


if __name__ == "__main__":
    lancer_traitement()
