# modules/module_3/handlers/stock_unified.py
"""
Interface unifiée pour l'alimentation du stock.
Alimente SIMULTANÉMENT stock.json ET PostgreSQL.
"""

from datetime import date as date_type
from pathlib import Path
from logging import getLogger

from modules.module_3 import stock as stock_json
from modules.module_3.handlers import db_stock

_log = getLogger("module_3.handlers.stock_unified")

def alimenter_stock_complet(
    num_caisse: str,
    date_caisse: str,
    donnees: dict
) -> bool:
    """
    Alimente le stock SIMULTANÉMENT en JSON et en PostgreSQL.

    Args:
        num_caisse: "1", "2", "kiosque", etc.
        date_caisse: "JJ/MM/YYYY" ou "YYYY-MM-DD"
        donnees: {
            'detail_especes': {"200": {"quantite": 5, "montant": 1000}, ...},
            'detail_cheques_vac': {"50": {"quantite": 2}, ...},
            'detail_cheques': [{"numero": "123", "montant": 150}, ...],
            'ancv_connect': {"total": 320.0}
        }

    Returns:
        bool: True si succès
    """
    _log.info(f"[STOCK_UNIFIED] Alimentation START caisse={num_caisse} date={date_caisse}")

    try:
        # ✅ 1. ALIMENTE JSON
        stock_json.alimenter_depuis_caisse(num_caisse, date_caisse, donnees)
        _log.debug("[STOCK_UNIFIED] ✅ JSON alimenté")

        # ✅ 2. ALIMENTE POSTGRESQL
        _alimenter_postgresql(num_caisse, date_caisse, donnees)
        _log.debug("[STOCK_UNIFIED] ✅ PostgreSQL alimenté")

        _log.info(f"[STOCK_UNIFIED] ✅ Stock complet alimenté")
        return True

    except Exception as err:
        _log.error(f"[STOCK_UNIFIED] ❌ Erreur : {err}", exc_info=True)
        return False


def _alimenter_postgresql(
    num_caisse: str,
    date_caisse: str,
    donnees: dict
) -> None:
    """Alimente les tables PostgreSQL."""
    _log.debug(f"[STOCK_UNIFIED] PostgreSQL : traitement caisse={num_caisse}")

    # ── ESPÈCES ──────────────────────────────────────────────────────
    detail_esp = donnees.get("detail_especes", {})
    for coupure_str, info in detail_esp.items():
        try:
            coupure = float(coupure_str)
            qte = int(info.get("quantite", 0)) if isinstance(info, dict) else 0
            montant = float(info.get("montant", 0)) if isinstance(info, dict) else qte * coupure

            if qte > 0:
                db_stock.maj_stock_espece(coupure, qte, montant, f"CAISSE_{num_caisse}")
                _log.debug(f"  ✅ Espèces : {coupure}€ x{qte} = {montant}€")
        except (ValueError, TypeError) as e:
            _log.warning(f"  ⚠️ Espèces {coupure_str} : {e}")

    # ── CHÈQUES VACANCES ─────────────────────────────────────────────
    detail_cv = donnees.get("detail_cheques_vac", {})
    for coupure_str, info in detail_cv.items():
        try:
            coupure = float(coupure_str)
            qte = int(info.get("quantite", 0)) if isinstance(info, dict) else 0
            montant = float(info.get("montant", 0)) if isinstance(info, dict) else qte * coupure

            if qte > 0:
                db_stock.maj_stock_cheque_vac(coupure, qte, montant, f"CAISSE_{num_caisse}")
                _log.debug(f"  ✅ Chèques Vac : {coupure}€ x{qte} = {montant}€")
        except (ValueError, TypeError) as e:
            _log.warning(f"  ⚠️ Chèques Vac {coupure_str} : {e}")

    # ── CHÈQUES ───────────────────────────────────────────────────────
    detail_ch = donnees.get("detail_cheques", [])
    if isinstance(detail_ch, list) and detail_ch:
        cheques_a_ajouter = []
        for ch in detail_ch:
            if isinstance(ch, dict):
                num = ch.get("numero") or ch.get("num")
                montant = float(ch.get("montant", 0)) if ch.get("montant") else 0.0

                if num and montant > 0:
                    cheques_a_ajouter.append({
                        "numero": str(num),
                        "montant": montant,
                        "date_caisse": date_caisse,
                        "caisse_ref": num_caisse,
                        "statut": "EN_STOCK"
                    })
                    _log.debug(f"  ✅ Chèque : {num} = {montant}€")

        if cheques_a_ajouter:
            db_stock.ajouter_cheques(cheques_a_ajouter)

    # ── ANCV ──────────────────────────────────────────────────────────
    ancv_data = donnees.get("ancv_connect", {})
    if isinstance(ancv_data, dict):
        montant_ancv = float(ancv_data.get("total", 0))
        if montant_ancv > 0:
            db_stock.ajouter_ancv(montant_ancv, num_caisse, _parse_date(date_caisse))
            _log.debug(f"  ✅ ANCV : {montant_ancv}€")

    _log.debug("[STOCK_UNIFIED] PostgreSQL traitement terminé")


def _parse_date(date_str: str) -> date_type:
    """Convertit "JJ/MM/YYYY" ou "YYYY-MM-DD" en date."""
    from datetime import datetime

    if "/" in date_str:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    else:
        return datetime.strptime(date_str, "%Y-%m-%d").date()


__all__ = ["alimenter_stock_complet"]
