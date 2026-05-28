# core/dispatcher.py

from pathlib import Path
import traceback
import sys

# ── Ajuster sys.path ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
    print(f"✅ Chemin ajouté : {BASE_DIR}")

# ── Import logger AVANT tout ──────────────────────────────────────────────────
from config import logger

logger.info("=" * 80)
logger.info("🚀 DISPATCHER INITIALISÉ")
logger.info("=" * 80)

# ── Détecteurs ────────────────────────────────────────────────────────────────
logger.info("📦 Chargement des détecteurs...")
try:
    from core.detecteur import (
        est_amex_caisse,
        est_amex_internet,
        est_avoirs,
        est_alma,
        est_ancv,
        est_kiosk_photo,
        est_ta,
        est_banque_internet,
        est_alpilink,
        est_compta_internet,
        est_planet,
    )
    logger.info("✅ Tous les détecteurs importés")
except Exception as e:
    logger.error(f"❌ Erreur import détecteurs : {e}")
    raise

# ── Module 1 : Handlers (ancien handlers/) ────────────────────────────────────
logger.info("📦 Chargement des handlers Module 1...")
try:
    from modules.module_1.handlers.traiter_ancv import traiter_ancv
    from modules.module_1.traiter_alma import traiter_alma
    from modules.module_1.handlers.traiter_amex_caisse import traiter_amex_caisse
    from modules.module_1.handlers.traiter_amex_internet import traiter_amex_internet
    from modules.module_1.handlers.traiter_banque import traiter_banque as traiter_banque_csv
    from modules.module_1.handlers.traiter_ta import traiter_ta
    from modules.module_1.handlers.traiter_avoirs import traiter_avoirs
    from modules.module_1.handlers.traiter_kiosk_photo import traiter_kiosk_photo
    from modules.module_1.handlers.traiter_planet import traiter_planet
    logger.info("✅ Module 1 chargé (9 handlers)")
except Exception as e:
    logger.error(f"❌ Erreur import Module 1 : {e}")
    traceback.print_exc()
    raise

# ── Module 2 : Handlers spécialisés ───────────────────────────────────────────
logger.info("📦 Chargement des handlers Module 2...")
try:
    from modules.module_2.handlers.banque_handler import traiter_banque
    from modules.module_2.handlers.alpilink_handler import traiter_alpilink
    from modules.module_2.handlers.compta_handler import traiter_compta
    from modules.module_2.justification_handler import JustificationHandler  # ✅ AJOUT
    logger.info("✅ Module 2 chargé (3 handlers + JustificationHandler)")
except Exception as e:
    logger.error(f"❌ Erreur import Module 2 : {e}")
    traceback.print_exc()
    raise


# ── Utils ─────────────────────────────────────────────────────────────────────
logger.info("📦 Chargement des utils...")
try:
    from core.utils.fichiers import convertir_xls_en_xlsx
    logger.info("✅ Utils chargées")
except Exception as e:
    logger.error(f"❌ Erreur import utils : {e}")
    raise

logger.info("=" * 80)
logger.info("✅ TOUS LES IMPORTS OK - DISPATCHER PRÊT")
logger.info("=" * 80)

# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCHER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def traiter_fichier(fichier: Path) -> dict:
    """
    Détecte le type de fichier et appelle le handler approprié.

    Args:
        fichier (Path): Chemin du fichier à traiter

    Returns:
        dict: Résultat du traitement
    """
    fichier = Path(fichier)

    if not fichier.exists():
        logger.error(f"❌ FICHIER INEXISTANT : {fichier.name}")
        logger.error(f"   Chemin absolu : {fichier.absolute()}")
        return {
            "statut": "ERREUR",
            "fichier": fichier.name,
            "message": "Fichier inexistant"
        }

    logger.info(f"\n{'=' * 80}")
    logger.info(f"📄 Traitement : {fichier.name}")
    logger.info(f"{'=' * 80}")

    try:
        # Convertir XLS → XLSX si nécessaire
        if fichier.suffix.lower() == ".xls":
            logger.info("🔄 Conversion XLS → XLSX...")
            fichier = convertir_xls_en_xlsx(fichier)
            logger.info(f"✅ Converti : {fichier.name}")

        # ── DÉTECTION ──────────────────────────────────────────────────────────
        handlers_a_appeler = []

        if est_amex_caisse(fichier):
            logger.info("💳 AMEX CAISSE détecté")
            handlers_a_appeler.append(("AMEX CAISSE", traiter_amex_caisse))

        if est_amex_internet(fichier):
            logger.info("🌐 AMEX INTERNET détecté")
            handlers_a_appeler.append(("AMEX INTERNET", traiter_amex_internet))

        if est_avoirs(fichier):
            logger.info("📝 AVOIRS détecté")
            handlers_a_appeler.append(("AVOIRS", traiter_avoirs))

        if est_alma(fichier):
            logger.info("🏪 ALMA détecté")
            handlers_a_appeler.append(("ALMA", traiter_alma))

        if est_ancv(fichier):
            logger.info("🎫 ANCV détecté")
            handlers_a_appeler.append(("ANCV", traiter_ancv))

        if est_kiosk_photo(fichier):
            logger.info("📸 KIOSK PHOTO détecté")
            handlers_a_appeler.append(("KIOSK PHOTO", traiter_kiosk_photo))

        if est_ta(fichier):
            logger.info("📊 TA détecté")
            handlers_a_appeler.append(("TA", traiter_ta))

        if est_banque_internet(fichier):
            logger.info("🏦 BANQUE INTERNET détecté")
            handlers_a_appeler.append(("BANQUE", traiter_banque))

        if est_alpilink(fichier):
            logger.info("🔗 ALPILINK détecté")
            handlers_a_appeler.append(("ALPILINK", traiter_alpilink))

        if est_compta_internet(fichier):
            logger.info("💼 COMPTA INTERNET détecté")
            handlers_a_appeler.append(("COMPTA", traiter_compta))

        if est_planet(fichier):
            logger.info("🌍 PLANET détecté")
            handlers_a_appeler.append(("PLANET", traiter_planet))

        # ── EXÉCUTION ──────────────────────────────────────────────────────────
        if not handlers_a_appeler:
            logger.warning(f"⚠️  AUCUN HANDLER DÉTECTÉ pour {fichier.name}")
            return {
                "statut": "AUCUN_HANDLER",
                "fichier": fichier.name,
                "message": "Aucun type de fichier reconnu"
            }

        resultats = []
        for nom_handler, handler_func in handlers_a_appeler:
            try:
                logger.info(f"\n► Appel {nom_handler}...")
                resultat = handler_func(fichier)
                resultats.append({
                    "handler": nom_handler,
                    "statut": "OK",
                    "resultat": resultat
                })
                logger.info(f"✅ {nom_handler} réussi")
            except Exception as e:
                logger.error(f"❌ Erreur {nom_handler} : {e}")
                traceback.print_exc()
                resultats.append({
                    "handler": nom_handler,
                    "statut": "ERREUR",
                    "message": str(e)
                })

        return {
            "statut": "SUCCÈS",
            "fichier": fichier.name,
            "handlers_executes": resultats
        }

    except Exception as e:
        logger.error(f"❌ ERREUR GLOBALE : {e}")
        traceback.print_exc()
        return {
            "statut": "ERREUR",
            "fichier": fichier.name,
            "message": str(e)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TEST PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logger.info("\n")
    logger.info("🧪 TEST FICHIER : dispatcher.py")
    logger.info("\n")

    # Si un argument est fourni
    if len(sys.argv) > 1:
        fichier_test = Path(sys.argv[1])
    else:
        # Chercher un fichier dans DOSSIER_BRUT
        try:
            from config import DOSSIER_BRUT
            fichiers = list(DOSSIER_BRUT.glob("*.*"))
            if fichiers:
                fichier_test = fichiers[0]
                logger.info(f"📝 Fichier trouvé : {fichier_test.name}")
            else:
                logger.warning("⚠️  Aucun fichier dans DOSSIER_BRUT")
                fichier_test = None
        except Exception as e:
            logger.error(f"❌ Erreur import config : {e}")
            fichier_test = None

    if fichier_test:
        resultat = traiter_fichier(fichier_test)

        logger.info("\n" + "=" * 80)
        logger.info(f"Résultat : {resultat['statut']}")
        logger.info("=" * 80)
    else:
        logger.info("Aucun fichier à traiter")
