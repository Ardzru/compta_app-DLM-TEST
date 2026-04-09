from pathlib import Path
from core.dispatcher import traiter_fichier
from logger import logger

from config import DOSSIER_BRUT
DOSSIER_FICHIERS = DOSSIER_BRUT


def lancer_traitement():
    succes = 0
    erreurs = 0

    logger.info("=== DÉBUT DU TRAITEMENT ===")

    if not DOSSIER_FICHIERS.exists():
        logger.error(f"Dossier introuvable : {DOSSIER_FICHIERS}")
        print("Dossier fichiers_brut introuvable")
        return

    for fichier in DOSSIER_FICHIERS.iterdir():
        if not fichier.is_file():
            continue

        try:
            traiter_fichier(fichier)
            succes += 1
        except Exception:
            erreurs += 1

    logger.info("=== FIN DU TRAITEMENT ===")
    logger.info(f"Succès : {succes}")
    logger.info(f"Erreurs : {erreurs}")

    print("Traitement terminé")
    print(f"Succès : {succes}")
    print(f"Erreurs : {erreurs}")
    print("Voir traitement.log pour le détail")


if __name__ == "__main__":
    lancer_traitement()
