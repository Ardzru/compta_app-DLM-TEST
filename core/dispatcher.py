from pathlib import Path
import traceback

from core.detecteur import (
    est_amex_caisse,
    est_amex_internet,
    est_avoirs,
    est_alma,
    est_ancv,
    est_kiosk_photo,
    est_ta,
)

from handlers.traiter_ancv import traiter_ancv
from handlers.traiter_alma import traiter_alma
from handlers.traiter_amex_caisse import traiter_amex_caisse
from handlers.traiter_amex_internet import traiter_amex_internet
from handlers.traiter_banque import traiter_banque
from handlers.traiter_ta import traiter_ta
from handlers.traiter_avoirs import traiter_avoirs
from handlers.traiter_kiosk_photo import traiter_kiosk_photo

from utils.convert_xls import convertir_xls_en_xlsx
from logger import logger


def traiter_fichier(fichier: Path) -> bool:
    """
    Traite un fichier comptable selon son type détecté.
    Retourne True si au moins un traitement a été appliqué.
    """

    try:
        traite = False

        # 🔁 Fichier utilisé pour le traitement (conversion si besoin)
        fichier_traitement = fichier
        if fichier.suffix.lower() == ".xls":
            fichier_traitement = convertir_xls_en_xlsx(fichier)

        # ==========================================================
        # 🔍 DÉTECTIONS - lecture unique par fichier
        # ==========================================================

        detected_amex_caisse   = est_amex_caisse(fichier_traitement)
        detected_amex_internet = est_amex_internet(fichier_traitement)
        detected_avoirs        = est_avoirs(fichier_traitement)
        detected_alma          = est_alma(fichier_traitement)
        detected_ancv          = est_ancv(fichier)          # CSV → pas de conversion
        detected_kiosk         = est_kiosk_photo(fichier)   # Détection par nom uniquement
        detected_ta            = est_ta(fichier_traitement)

        # ==========================================================
        # ⚙️ TRAITEMENTS (ORDRE IMPORTANT)
        # ==========================================================

        if detected_amex_caisse:
            logger.info(f"AMEX CAISSE détecté : {fichier.name}")
            traiter_amex_caisse(fichier_traitement)
            traite = True

        if detected_amex_internet:
            logger.info(f"AMEX INTERNET détecté : {fichier.name}")
            traiter_amex_internet(fichier_traitement)
            traite = True

        if detected_avoirs:
            logger.info(f"AVOIRS détecté : {fichier.name}")
            traiter_avoirs(fichier_traitement)
            traite = True

        if detected_alma:
            logger.info(f"ALMA détecté : {fichier.name}")
            traiter_alma(fichier_traitement)
            traite = True

        if detected_ancv:
            logger.info(f"ANCV détecté : {fichier.name}")
            traiter_ancv(fichier_traitement)
            traite = True

        # ==========================================================
        # 📸 KIOSK PHOTO LUGE (AVANT BANQUE)
        # ==========================================================

        if detected_kiosk:
            logger.info(f"KIOSK PHOTO LUGE détecté : {fichier.name}")
            traiter_kiosk_photo(fichier_traitement)
            traite = True

        # ==========================================================
        # 🏦 BANQUE (FALLBACK CSV)
        # ==========================================================

        if (
            fichier.suffix.lower() == ".csv"
            and not detected_ancv       # ← résultat stocké, pas de 2ème lecture
            and not detected_kiosk      # ← un fichier kiosk n'est pas un fichier banque
            and not traite
        ):
            try:
                logger.info(f"BANQUE tentative : {fichier.name}")
                traiter_banque(fichier_traitement)
                traite = True
            except Exception:
                logger.warning(f"BANQUE non reconnu : {fichier.name}")

        # ==========================================================
        # 🎟️ TA
        # ==========================================================

        if detected_ta:
            logger.info(f"TA détecté : {fichier.name}")
            traiter_ta(fichier_traitement)
            traite = True

        # ==========================================================
        # ⚠️ AUCUN TRAITEMENT
        # ==========================================================

        if not traite:
            logger.warning(f"Aucun traitement applicable : {fichier.name}")

        return traite

    except Exception:
        logger.error(f"Erreur critique sur {fichier.name}")
        logger.error(traceback.format_exc())
        raise
