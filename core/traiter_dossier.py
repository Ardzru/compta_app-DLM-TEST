"""
===============================================================================
traiter_dossier.py
===============================================================================
Point d'entrée principal : traitement batch de tous les fichiers bruts
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
ARCHIVE_BASE = Path("archive")
LOCK_FILE = Path("traitement.lock")
BACKUP_DIR = Path("backups")


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def verrouiller_traitement() -> bool:
    """
    Créer un lock file pour éviter les traitements parallèles.

    Returns:
        True si lock créé (traitement lancé)
        False si lock existe déjà (traitement en cours)
    """
    if LOCK_FILE.exists():
        logger.warning("⚠️  Traitement déjà en cours — abandon")
        return False

    LOCK_FILE.touch()
    logger.debug(f"🔒 Lock file créé : {LOCK_FILE}")
    return True


def deverrouiller_traitement():
    """Supprimer le lock file."""
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        logger.debug(f"🔓 Lock file supprimé")


def preparer_environnement():
    """Créer les dossiers nécessaires."""
    try:
        creer_dossier(DOSSIER_FICHIERS)
        creer_dossier(ARCHIVE_BASE)
        creer_dossier(BACKUP_DIR)
        logger.debug("✅ Environnement préparé")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur préparation environnement : {e}")
        return False


def traiter_fichier_xls(fichier: Path) -> bool:
    """
    Traiter un fichier XLS (conversion + traitement).

    Args:
        fichier: Chemin du fichier XLS

    Returns:
        True si traitement réussi
    """
    try:
        logger.info(f"📄 Conversion XLS → XLSX : {fichier.name}")

        # Conversion XLS → XLSX
        fichier_xlsx = convertir_xls_en_xlsx(str(fichier))

        if fichier_xlsx is None:
            logger.error(f"❌ Conversion échouée : {fichier.name}")
            return False

        # Traiter le XLSX
        succes = traiter_fichier(fichier_xlsx)

        if succes:
            # Supprimer le fichier XLSX converti (temporaire)
            supprimer_fichier(fichier_xlsx)
            logger.info(f"🧹 Fichier temporaire supprimé : {Path(fichier_xlsx).name}")

        return succes

    except Exception as e:
        logger.error(f"❌ Erreur traitement XLS : {e}")
        return False


def traiter_fichier_xlsx(fichier: Path) -> bool:
    """
    Traiter un fichier XLSX directement.

    Args:
        fichier: Chemin du fichier XLSX

    Returns:
        True si traitement réussi
    """
    try:
        logger.info(f"📊 Traitement XLSX : {fichier.name}")
        return traiter_fichier(fichier)

    except Exception as e:
        logger.error(f"❌ Erreur traitement XLSX : {e}")
        return False


def traiter_fichier_csv(fichier: Path) -> bool:
    """
    Traiter un fichier CSV directement.

    Args:
        fichier: Chemin du fichier CSV

    Returns:
        True si traitement réussi
    """
    try:
        logger.info(f"📋 Traitement CSV : {fichier.name}")
        return traiter_fichier(fichier)

    except Exception as e:
        logger.error(f"❌ Erreur traitement CSV : {e}")
        return False


def traiter_fichier_brut(fichier: Path) -> bool:
    """
    Dispatcher pour traiter un fichier selon son extension.

    Args:
        fichier: Path du fichier

    Returns:
        True si traitement réussi
    """
    extension = fichier.suffix.lower()

    if extension == ".xls":
        return traiter_fichier_xls(fichier)
    elif extension == ".xlsx":
        return traiter_fichier_xlsx(fichier)
    elif extension == ".csv":
        return traiter_fichier_csv(fichier)
    else:
        logger.warning(f"⚠️  Extension non reconnue : {extension} ({fichier.name})")
        return False


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def lancer_traitement():
    """
    Lance le traitement batch de tous les fichiers bruts.

    Workflow :
    1. Vérifier le lock file
    2. Préparer environnement
    3. Pour chaque fichier brut :
       - Traiter selon extension
       - Archiver fichier original
       - Supprimer fichiers temporaires
    4. Afficher résumé
    """

    # 🔒 VERROUILLAGE
    if not verrouiller_traitement():
        return

    succes = 0
    erreurs = 0
    ignorés = 0

    try:
        # 📦 PRÉPARATION
        logger.info("=" * 80)
        logger.info("🚀 DÉBUT DU TRAITEMENT BATCH")
        logger.info("=" * 80)

        if not preparer_environnement():
            logger.error("❌ Impossible de préparer l'environnement")
            return

        # 📂 LISTAGE FICHIERS
        fichiers = lister_fichiers_bruts(DOSSIER_FICHIERS)

        if not fichiers:
            logger.info("✅ Aucun fichier à traiter")
            return

        logger.info(f"📊 {len(fichiers)} fichier(s) à traiter")
        logger.info("-" * 80)

        # 🔁 TRAITEMENT
        for fichier in fichiers:
            try:
                logger.info(f"\n📍 Traitement : {fichier.name}")

                # Vérifier que le fichier existe toujours
                if not fichier.exists():
                    logger.warning(f"⚠️  Fichier supprimé entre temps : {fichier.name}")
                    ignorés += 1
                    continue

                # 🔨 TRAITEMENT PRINCIPAL
                traite = traiter_fichier_brut(fichier)

                if traite:
                    succes += 1

                    # 📦 ARCHIVAGE
                    if fichier.exists():
                        chemin_archive = archiver_fichier(
                            fichier,
                            ARCHIVE_BASE,
                            creer_subdir_jour=True
                        )

                        if chemin_archive:
                            logger.info(f"✅ Archivé : {Path(chemin_archive).name}")
                        else:
                            logger.error(f"❌ Erreur archivage : {fichier.name}")
                            erreurs += 1
                            succes -= 1
                else:
                    logger.warning(f"⚠️  Fichier ignoré : {fichier.name}")
                    ignorés += 1

            except Exception as e:
                erreurs += 1
                logger.exception(f"❌ Erreur fatale sur {fichier.name}")

        # 📊 RÉSUMÉ
        logger.info("\n" + "=" * 80)
        logger.info("📊 RÉSUMÉ DU TRAITEMENT")
        logger.info("=" * 80)
        logger.info(f"✅ Traités avec succès   : {succes}")
        logger.info(f"⚠️  Ignorés              : {ignorés}")
        logger.info(f"❌ Erreurs              : {erreurs}")
        logger.info(f"📊 Total                : {len(fichiers)}")
        logger.info("=" * 80 + "\n")

    except Exception as e:
        logger.exception("❌ ERREUR CRITIQUE DANS LE TRAITEMENT")
        erreurs += 1

    finally:
        # 🔓 DÉVERROUILLAGE
        deverrouiller_traitement()


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    lancer_traitement()
