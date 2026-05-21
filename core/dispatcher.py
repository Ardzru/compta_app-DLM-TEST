# core/dispatcher.py

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
    est_banque_internet,
    est_alpilink,
    est_compta_internet,
    est_planet,
)

from handlers.module_1.traiter_ancv           import traiter_ancv
from handlers.module_1.traiter_alma           import traiter_alma
from handlers.module_1.traiter_amex_caisse    import traiter_amex_caisse
from handlers.module_1.traiter_amex_internet  import traiter_amex_internet
from handlers.module_1.traiter_banque         import traiter_banque as traiter_banque_csv
from handlers.module_1.traiter_ta             import traiter_ta
from handlers.module_1.traiter_avoirs         import traiter_avoirs
from handlers.module_1.traiter_kiosk_photo    import traiter_kiosk_photo
from handlers.module_1.traiter_planet         import traiter_planet
from handlers.module_2.banque_handler         import traiter_banque
from handlers.module_2.alpilink_handler       import traiter_alpilink
from handlers.module_2.compta_handler         import traiter_compta


from utils.convert_xls import convertir_xls_en_xlsx
from logger import logger


def traiter_fichier(fichier: Path) -> bool:
    """
    Traite un fichier comptable selon son type détecté.
    Retourne True si au moins un traitement a été appliqué.
    """
    try:
        traite = False

        # 🔁 Conversion si besoin
        fichier_traitement = fichier
        if fichier.suffix.lower() == ".xls":
            fichier_traitement = convertir_xls_en_xlsx(fichier)

        # ==========================================================
        # 🔍 DÉTECTIONS EXISTANTES
        # ==========================================================
        detected_amex_caisse   = est_amex_caisse(fichier_traitement)
        detected_amex_internet = est_amex_internet(fichier_traitement)
        detected_avoirs        = est_avoirs(fichier_traitement)
        detected_alma          = est_alma(fichier_traitement)
        detected_ancv          = est_ancv(fichier)
        detected_kiosk         = est_kiosk_photo(fichier)
        detected_ta            = est_ta(fichier_traitement)

        # ==========================================================
        # 🔍 NOUVELLES DÉTECTIONS
        # ==========================================================
        detected_banque_internet  = est_banque_internet(fichier_traitement)
        detected_alpilink         = est_alpilink(fichier_traitement)
        detected_compta_internet  = est_compta_internet(fichier_traitement)

        # ==========================================================
        # ⚙️ TRAITEMENTS EXISTANTS (inchangés)
        # ==========================================================
        if detected_amex_caisse:
            logger.info(f"AMEX CAISSE détecté : {fichier.name}")
            traiter_amex_caisse(fichier_traitement)
            traite = True

        if detected_amex_internet:
            logger.info(f"AMEX INTERNET détecté : {fichier.name}")
            traiter_amex_internet(fichier_traitement)
            traite = True

        if est_planet(fichier_traitement):
            logger.info(f"PLANET détecté : {fichier.name}")
            traiter_planet(fichier_traitement)
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

        if detected_kiosk:
            logger.info(f"KIOSK PHOTO LUGE détecté : {fichier.name}")
            traiter_kiosk_photo(fichier_traitement)
            traite = True

        # BANQUE CSV (fallback existant — inchangé)
        if (
            fichier.suffix.lower() == ".csv"
            and not detected_ancv
            and not detected_kiosk
            and not traite
        ):
            try:
                logger.info(f"BANQUE CSV tentative : {fichier.name}")
                traiter_banque_csv(fichier_traitement)
                traite = True
            except Exception:
                logger.warning(f"BANQUE CSV non reconnu : {fichier.name}")

        if detected_ta:
            logger.info(f"TA détecté : {fichier.name}")
            traiter_ta(fichier_traitement)
            traite = True

        # ==========================================================
        # ⚙️ NOUVEAUX TRAITEMENTS
        # ==========================================================

        # 🏦 BANQUE INTERNET (AMEX / PLANET / CB)
        if detected_banque_internet and not detected_amex_caisse:
            logger.info(f"BANQUE INTERNET détecté : {fichier.name}")
            traiter_banque(fichier_traitement)
            traite = True

        # 🗂️ ALPILINK (+ BuyClub inclus)
        if detected_alpilink:
            logger.info(f"ALPILINK détecté : {fichier.name}")
            traiter_alpilink(fichier_traitement)
            traite = True

        # 📒 COMPTA INTERNET
        if detected_compta_internet:
            logger.info(f"COMPTA INTERNET détecté : {fichier.name}")
            traiter_compta(fichier_traitement)
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
