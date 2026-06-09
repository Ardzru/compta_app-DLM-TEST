"""
===============================================================================
traiter_dossier.py
===============================================================================
Point d'entree principal : traitement batch de tous les fichiers bruts
Utilise utils_fichiers pour navigation et archivage
===============================================================================
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.dispatcher import traiter_fichier
from core.utils.fichiers import (
    lister_fichiers_bruts,
    archiver_fichier,
    supprimer_fichier,
    convertir_xls_en_xlsx,
    creer_dossier,
)
from config import logger

# ============================================================================
# CONFIGURATION
# ============================================================================

DOSSIER_FICHIERS = Path("fichiers_brut")
ARCHIVE_BASE     = Path("archive")
LOCK_FILE        = Path("traitement.lock")
BACKUP_DIR       = Path("backups")

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def verrouiller_traitement() -> bool:
    """
    Creer un lock file pour eviter les traitements paralleles.

    Returns:
        True si lock cree (traitement lance)
        False si lock existe deja (traitement en cours)
    """
    if LOCK_FILE.exists():
        logger.warning("Traitement deja en cours — abandon")
        return False

    LOCK_FILE.touch()
    logger.debug(f"Lock file cree : {LOCK_FILE}")
    return True


def deverrouiller_traitement():
    """Supprimer le lock file."""
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        logger.debug("Lock file supprime")


def preparer_environnement() -> bool:
    """Creer les dossiers necessaires."""
    try:
        creer_dossier(DOSSIER_FICHIERS)
        creer_dossier(ARCHIVE_BASE)
        creer_dossier(BACKUP_DIR)
        logger.debug("Environnement prepare")
        return True
    except Exception:
        logger.exception("Erreur preparation environnement")
        return False


def traiter_fichier_xls(fichier: Path) -> bool:
    """
    Traiter un fichier XLS (conversion + traitement).

    Args:
        fichier: Chemin du fichier XLS

    Returns:
        True si traitement reussi
    """
    try:
        logger.info(f"Conversion XLS -> XLSX : {fichier.name}")

        fichier_xlsx = convertir_xls_en_xlsx(fichier)

        if fichier_xlsx is None:
            logger.error(f"Conversion echouee : {fichier.name}")
            return False

        resultat = traiter_fichier(fichier_xlsx)
        succes = resultat.get("statut") == "SUCCES"

        if succes:
            supprimer_fichier(fichier_xlsx)
            logger.info(f"Fichier temporaire supprime : {Path(fichier_xlsx).name}")

        return succes

    except Exception:
        logger.exception(f"Erreur traitement XLS : {fichier.name}")
        return False


def traiter_fichier_xlsx(fichier: Path) -> bool:
    """
    Traiter un fichier XLSX directement.

    Args:
        fichier: Chemin du fichier XLSX

    Returns:
        True si traitement reussi
    """
    try:
        logger.info(f"Traitement XLSX : {fichier.name}")
        resultat = traiter_fichier(fichier)
        return resultat.get("statut") == "SUCCES"

    except Exception:
        logger.exception(f"Erreur traitement XLSX : {fichier.name}")
        return False


def traiter_fichier_csv(fichier: Path) -> bool:
    """
    Traiter un fichier CSV directement.

    Args:
        fichier: Chemin du fichier CSV

    Returns:
        True si traitement reussi
    """
    try:
        logger.info(f"Traitement CSV : {fichier.name}")
        resultat = traiter_fichier(fichier)
        return resultat.get("statut") == "SUCCES"

    except Exception:
        logger.exception(f"Erreur traitement CSV : {fichier.name}")
        return False


def traiter_fichier_brut(fichier: Path) -> bool:
    """
    Dispatcher pour traiter un fichier selon son extension.

    Args:
        fichier: Path du fichier

    Returns:
        True si traitement reussi
    """
    extension = fichier.suffix.lower()

    if extension == ".xls":
        return traiter_fichier_xls(fichier)
    elif extension == ".xlsx":
        return traiter_fichier_xlsx(fichier)
    elif extension == ".csv":
        return traiter_fichier_csv(fichier)
    else:
        logger.warning(f"Extension non reconnue : {extension} ({fichier.name})")
        return False


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def lancer_traitement():
    """
    Lance le traitement batch de tous les fichiers bruts.

    Workflow :
    1. Verifier le lock file
    2. Preparer environnement
    3. Pour chaque fichier brut :
       - Traiter selon extension
       - Archiver fichier original
       - Supprimer fichiers temporaires
    4. Afficher resume
    """

    if not verrouiller_traitement():
        return

    succes  = 0
    erreurs = 0
    ignores = 0

    try:
        logger.info("=" * 80)
        logger.info("DEBUT DU TRAITEMENT BATCH")
        logger.info("=" * 80)

        if not preparer_environnement():
            logger.error("Impossible de preparer l'environnement")
            return

        fichiers = lister_fichiers_bruts(DOSSIER_FICHIERS)

        if not fichiers:
            logger.info("Aucun fichier a traiter")
            return

        logger.info(f"{len(fichiers)} fichier(s) a traiter")
        logger.info("-" * 80)

        for fichier in fichiers:
            try:
                logger.info(f"Traitement : {fichier.name}")

                if not fichier.exists():
                    logger.warning(f"Fichier supprime entre temps : {fichier.name}")
                    ignores += 1
                    continue

                traite = traiter_fichier_brut(fichier)

                if traite:
                    succes += 1

                    if fichier.exists():
                        chemin_archive = archiver_fichier(
                            fichier,
                            ARCHIVE_BASE,
                            creer_subdir_jour=True,
                        )

                        if chemin_archive:
                            logger.info(f"Archive : {Path(chemin_archive).name}")
                        else:
                            logger.error(f"Erreur archivage : {fichier.name}")
                            erreurs += 1
                            succes  -= 1
                else:
                    logger.warning(f"Fichier ignore : {fichier.name}")
                    ignores += 1

            except Exception:
                erreurs += 1
                logger.exception(f"Erreur fatale sur {fichier.name}")

        logger.info("=" * 80)
        logger.info("RESUME DU TRAITEMENT")
        logger.info("=" * 80)
        logger.info(f"Traites avec succes : {succes}")
        logger.info(f"Ignores             : {ignores}")
        logger.info(f"Erreurs             : {erreurs}")
        logger.info(f"Total               : {len(fichiers)}")
        logger.info("=" * 80)

    except Exception:
        logger.exception("ERREUR CRITIQUE DANS LE TRAITEMENT")
        erreurs += 1

    finally:
        deverrouiller_traitement()


# ============================================================================
# POINT D'ENTREE
# ============================================================================

if __name__ == "__main__":
    lancer_traitement()
