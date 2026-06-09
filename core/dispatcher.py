# core/dispatcher.py
from pathlib import Path
from config import logger
from core.utils.convert_xls import convertir_xls_en_xlsx
from core.detecteur import (
    est_amex_caisse, est_amex_internet,
    est_avoirs, est_alma,
    est_ancv, est_ancv_banque,
    est_kiosk_photo, est_ta,
    est_banque_internet, est_alpilink, est_compta_internet,
    est_planet_caisse, est_planet_internet,
)

# ═══════════════════════════════════════════════════════════════════════════════
# TABLE DE ROUTING MODULE 1
# ⚠️ L'ordre est important :
#    - ANCV_BANQUE avant ANCV (même extension .csv)
#    - PLANET INTERNET avant PLANET CAISSE
# ═══════════════════════════════════════════════════════════════════════════════

_HANDLERS_M1 = [
    (
        "AMEX CAISSE",
        est_amex_caisse,
        "modules.module_1.handlers.traiter_amex_caisse",
        "traiter_amex_caisse",
    ),
    (
        "AMEX INTERNET",
        est_amex_internet,
        "modules.module_1.handlers.traiter_amex_internet",
        "traiter_amex_internet",
    ),
    (
        "PLANET INTERNET",
        est_planet_internet,
        "modules.module_1.handlers.traiter_planet_internet",
        "traiter_planet_internet",
    ),
    (
        "PLANET CAISSE",
        est_planet_caisse,
        "modules.module_1.handlers.traiter_planet_caisse",
        "traiter_planet_caisse",
    ),
    (
        "AVOIRS",
        est_avoirs,
        "modules.module_1.handlers.traiter_avoirs",
        "traiter_avoirs",
    ),
    (
        "ALMA",
        est_alma,
        "modules.module_1.handlers.traiter_alma",
        "traiter_alma",
    ),
    (
        "ANCV BANQUE",                                      # ⚠️ Avant ANCV classique
        est_ancv_banque,
        "modules.module_1.handlers.traiter_ancv_banque",
        "traiter_ancv_banque",
    ),
    (
        "ANCV",
        est_ancv,
        "modules.module_1.handlers.traiter_ancv",
        "traiter_ancv",
    ),
    (
        "KIOSK PHOTO",
        est_kiosk_photo,
        "modules.module_1.handlers.traiter_kiosk_photo",
        "traiter_kiosk_photo",
    ),
    (
        "TA",
        est_ta,
        "modules.module_1.handlers.traiter_ta",
        "traiter_ta",
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# TABLE DE ROUTING MODULE 2
# ═══════════════════════════════════════════════════════════════════════════════

_HANDLERS_M2 = [
    (
        "BANQUE INTERNET",
        est_banque_internet,
        "modules.module_2.handlers.banque_handler",
        "traiter_banque",
    ),
    (
        "ALPILINK",
        est_alpilink,
        "modules.module_2.handlers.alpilink_handler",
        "traiter_alpilink",
    ),
    (
        "COMPTA INTERNET",
        est_compta_internet,
        "modules.module_2.handlers.compta_handler",
        "traiter_compta_internet",
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def _appeler_handler(module_path: str, fn_name: str, fichier: Path):
    import importlib
    mod = importlib.import_module(module_path)
    fn  = getattr(mod, fn_name)
    fn(fichier)

# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════════

def traiter_fichier(fichier: Path) -> tuple:
    fichier = Path(fichier)
    fichier_original = fichier

    # Conversion XLS → XLSX si nécessaire
    if fichier.suffix.lower() == ".xls":
        fichier = convertir_xls_en_xlsx(fichier)

    try:
        # --- Module 1 ---
        for nom, detecteur, mod_path, fn_name in _HANDLERS_M1:
            if detecteur(fichier):
                logger.info(f"[DISPATCHER] {nom} → {fichier.name}")
                _appeler_handler(mod_path, fn_name, fichier)
                return ("SUCCES", f"{nom} traité")

        # --- Banque CSV (fichier original .csv) ---
        if fichier_original.suffix.lower() == ".csv":
            try:
                from modules.module_1.handlers.traiter_banque import traiter_banque
                traiter_banque(fichier_original)
                return ("SUCCES", "BANQUE CSV traité")
            except Exception as e:
                logger.warning(f"[DISPATCHER] BANQUE CSV échoué : {e}")

        # --- Module 2 ---
        for nom, detecteur, mod_path, fn_name in _HANDLERS_M2:
            if detecteur(fichier):
                logger.info(f"[DISPATCHER] {nom} → {fichier.name}")
                _appeler_handler(mod_path, fn_name, fichier)
                return ("SUCCES", f"{nom} traité")

        # --- Format inconnu ---
        logger.warning(f"[DISPATCHER] Format non reconnu : {fichier.name}")
        return ("FORMAT_INCONNU", f"Format non reconnu : {fichier.name}")

    except Exception as e:
        logger.error(
            f"[DISPATCHER] ERREUR {fichier.name} : {e}", exc_info=True
        )
        return ("ERREUR", str(e))
