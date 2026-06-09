"""
Opérations PostgreSQL sur la table caisses_validees.
Appelé depuis caisses_ui via verification.py — jamais directement depuis core/.
"""

from datetime import datetime
from typing import Optional
from config import logger
from core.database import get_cursor
import json as _json

# =============================================================================
# LECTURE
# =============================================================================

def caisse_existe(date_str: str, numero_caisse: str) -> bool:
    """Vérifie si une caisse est déjà enregistrée pour cette date."""
    date_fmt = _parse_date(date_str)
    if not date_fmt:
        return False
    try:
        with get_cursor() as cur:
            cur.execute(
                "SELECT 1 FROM caisses_validees WHERE date_caisse = %s AND numero_caisse = %s",
                (date_fmt, numero_caisse),
            )
            return cur.fetchone() is not None
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[DB_CAISSES] Erreur vérification existence : {exc}")
        return False

def charger_caisse_db(date_str: str, numero_caisse: str) -> Optional[dict]:
    """Charge une caisse validée depuis la DB."""
    date_fmt = _parse_date(date_str)
    if not date_fmt:
        return None
    try:
        with get_cursor() as cur:
            cur.execute(
                "SELECT * FROM caisses_validees WHERE date_caisse = %s AND numero_caisse = %s",
                (date_fmt, numero_caisse),
            )
            row = cur.fetchone()
            if row:
                logger.info(f"[DB_CAISSES] Caisse {numero_caisse} chargée ({date_str})")
                return dict(row)
            return None
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[DB_CAISSES] Erreur lecture caisse {numero_caisse} : {exc}")
        return None

# =============================================================================
# ÉCRITURE
# =============================================================================

def sauvegarder_caisse_db(date_str: str, numero_caisse: str, data: dict) -> bool:
    """
    INSERT ou UPDATE d'une caisse dans caisses_validees.

    Args:
        date_str      : "JJ/MM/AAAA"
        numero_caisse : "1", "2", ...
        data          : dict avec les clés correspondant aux colonnes MODES
                        + 'detail_especes', 'detail_cheques_vac', etc.
    Returns:
        bool
    """
    date_fmt = _parse_date(date_str)
    if not date_fmt:
        logger.error(f"[DB_CAISSES] Date invalide : {date_str}")
        return False

    # Colonnes numériques mappées depuis MODES
    champs_numeriques = [
        "especes_bande", "cb_sans_contact", "cb_visa", "dcc_planet",
        "amex", "amex_sans_contact", "ancv_connect", "cheques_vac_bande",
        "bons_livraisons", "cheques_bande", "paiement_web", "virement", "cb_vad",
    ]

    def _val(key):
        v = data.get(key)
        if v is None:
            return 0.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    # Calculs dérivés
    tous_modes = data.get("tous_modes", data)
    total_especes = _val("especes_bande")
    total_paiements = sum(_val(k) for k in champs_numeriques)

    detail_especes    = tous_modes.get("detail_especes", {})
    detail_cheques_vac = tous_modes.get("detail_cheques_vac", {})
    detail_ancv       = tous_modes.get("detail_ancv", {})
    detail_cheques    = tous_modes.get("detail_cheques", {})

    params = {
        "date_caisse":    date_fmt,
        "numero_caisse":  numero_caisse,
        "valide_le":      datetime.now(),
        "statut":         "validee",
        # montants
        "especes_bande":       _val("especes_bande"),
        "cb_sans_contact":     _val("cb_sans_contact"),
        "cb_visa":             _val("cb_visa"),
        "dcc_planet":          _val("dcc_planet"),
        "amex":                _val("amex"),
        "amex_sans_contact":   _val("amex_sans_contact"),
        "ancv_connect":        _val("ancv_connect"),
        "cheques_vac_bande":   _val("cheques_vac_bande"),
        "bons_livraisons":     _val("bons_livraisons"),
        "cheques_bande":       _val("cheques_bande"),
        "paiement_web":        _val("paiement_web"),
        "virement":            _val("virement"),
        "cb_vad":              _val("cb_vad"),
        "total_especes_compte": total_especes,
        "total_paiements":     total_paiements,
        # jsonb
        "detail_especes":     _json.dumps(detail_especes,     ensure_ascii=False),
        "detail_cheques_vac": _json.dumps(detail_cheques_vac, ensure_ascii=False),
        "detail_ancv":        _json.dumps(detail_ancv,        ensure_ascii=False),
        "detail_cheques":     _json.dumps(detail_cheques,     ensure_ascii=False),
    }

    sql_insert = """
        INSERT INTO caisses_validees (
            date_caisse, numero_caisse, valide_le, statut,
            especes_bande, cb_sans_contact, cb_visa, dcc_planet,
            amex, amex_sans_contact, ancv_connect, cheques_vac_bande,
            bons_livraisons, cheques_bande, paiement_web, virement, cb_vad,
            total_especes_compte, total_paiements,
            detail_especes, detail_cheques_vac, detail_ancv, detail_cheques
        ) VALUES (
            %(date_caisse)s, %(numero_caisse)s, %(valide_le)s, %(statut)s,
            %(especes_bande)s, %(cb_sans_contact)s, %(cb_visa)s, %(dcc_planet)s,
            %(amex)s, %(amex_sans_contact)s, %(ancv_connect)s, %(cheques_vac_bande)s,
            %(bons_livraisons)s, %(cheques_bande)s, %(paiement_web)s, %(virement)s, %(cb_vad)s,
            %(total_especes_compte)s, %(total_paiements)s,
            %(detail_especes)s::jsonb, %(detail_cheques_vac)s::jsonb,
            %(detail_ancv)s::jsonb, %(detail_cheques)s::jsonb
        )
        ON CONFLICT (date_caisse, numero_caisse) DO UPDATE SET
            valide_le             = EXCLUDED.valide_le,
            statut                = EXCLUDED.statut,
            especes_bande         = EXCLUDED.especes_bande,
            cb_sans_contact       = EXCLUDED.cb_sans_contact,
            cb_visa               = EXCLUDED.cb_visa,
            dcc_planet            = EXCLUDED.dcc_planet,
            amex                  = EXCLUDED.amex,
            amex_sans_contact     = EXCLUDED.amex_sans_contact,
            ancv_connect          = EXCLUDED.ancv_connect,
            cheques_vac_bande     = EXCLUDED.cheques_vac_bande,
            bons_livraisons       = EXCLUDED.bons_livraisons,
            cheques_bande         = EXCLUDED.cheques_bande,
            paiement_web          = EXCLUDED.paiement_web,
            virement              = EXCLUDED.virement,
            cb_vad                = EXCLUDED.cb_vad,
            total_especes_compte  = EXCLUDED.total_especes_compte,
            total_paiements       = EXCLUDED.total_paiements,
            detail_especes        = EXCLUDED.detail_especes,
            detail_cheques_vac    = EXCLUDED.detail_cheques_vac,
            detail_ancv           = EXCLUDED.detail_ancv,
            detail_cheques        = EXCLUDED.detail_cheques
    """

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(sql_insert, params)
        logger.info(f"[DB_CAISSES] ✅ Caisse {numero_caisse} sauvegardée ({date_str})")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[DB_CAISSES] ❌ Erreur sauvegarde caisse {numero_caisse} : {exc}")
        return False

# =============================================================================
# UTILITAIRES
# =============================================================================

def _parse_date(date_str: str):
    """Convertit JJ/MM/AAAA → date Python. Retourne None si invalide."""
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        logger.warning(f"[DB_CAISSES] Format date invalide : {date_str}")
        return None
