# modules/module_3/stock.py
"""
Gestion du stock des remises.
Tracking des espèces, chèques, chèques vacances et ANCV en caisse.
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from core.utils.montant import to_float
from core.utils.fichiers import creer_dossier

logger = logging.getLogger(__name__)

STOCK_FILE = Path("data/stock.json")


# ══════════════════════════════════════════════════════════════════════════════
# STRUCTURE STOCK
# ══════════════════════════════════════════════════════════════════════════════
# {
#   "especes":     {"200": 5, "100": 3, ...},   ← quantités par coupure
#   "cheques_vac": {"50": 2, "25": 8, ...},
#   "cheques":     [{"num": "1234567", "montant": 150.0}, ...],
#   "ancv":        {"total": 320.0},
#   "derniere_maj": "2026-05-13 15:08",
#   "historique":  [...]   ← log des alimentations
# }


# ══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════

def _charger() -> dict:
    """Charge le stock depuis le fichier JSON."""
    if not STOCK_FILE.exists():
        creer_dossier(STOCK_FILE.parent)
        return _stock_vide()
    try:
        return json.loads(STOCK_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Erreur lecture stock.json : {e}")
        return _stock_vide()


def _stock_vide() -> dict:
    """Retourne un stock vide."""
    return {
        "especes": {},
        "cheques_vac": {},
        "cheques": [],
        "ancv": {"total": 0.0},
        "derniere_maj": None,
        "historique": []
    }


def _sauvegarder(data: dict):
    """Sauvegarde le stock dans le fichier JSON."""
    try:
        creer_dossier(STOCK_FILE.parent)
        STOCK_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"Erreur sauvegarde stock.json : {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ALIMENTATION DU STOCK (depuis les caisses)
# ══════════════════════════════════════════════════════════════════════════════

def alimenter_depuis_caisse(num_caisse: str, date_caisse: str, donnees: dict):
    """
    Alimente le stock depuis une caisse.

    Args:
        num_caisse: Numéro de la caisse
        date_caisse: Date de la caisse (YYYY-MM-DD)
        donnees: Dict avec clés :
            - detail_especes: {"200": {"quantite": 5}, ...}
            - detail_cheques_vac: {"50": {"quantite": 2}, ...}
            - detail_cheques: [{"numero": "123", "montant": 150}, ...]
            - ancv_connect: {"total": 320.0}
    """
    logger.info(f"=== ALIMENTATION STOCK caisse {num_caisse} ===")
    logger.info(f"  detail_especes     : {donnees.get('detail_especes')}")
    logger.info(f"  detail_cheques_vac : {donnees.get('detail_cheques_vac')}")
    logger.info(f"  detail_cheques     : {donnees.get('detail_cheques')}")
    logger.info(f"  ancv_connect       : {donnees.get('ancv_connect')}")

    stock = _charger()
    log_entry = {
        "caisse": num_caisse,
        "date": date_caisse,
        "alimente_le": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ajouts": {}
    }

    # ── ESPÈCES ──────────────────────────────────────────────────
    detail_esp = donnees.get("detail_especes", {})
    for coupure, info in detail_esp.items():
        qte = info.get("quantite", 0) if isinstance(info, dict) else 0
        if qte > 0:
            coupure_str = str(coupure)
            stock["especes"][coupure_str] = stock["especes"].get(coupure_str, 0) + qte
            log_entry["ajouts"][f"especes_{coupure}"] = f"+{qte}"

    # ── CHÈQUES VACANCES ─────────────────────────────────────────
    detail_cv = donnees.get("detail_cheques_vac", {})
    for coupure, info in detail_cv.items():
        qte = info.get("quantite", 0) if isinstance(info, dict) else 0
        if qte > 0:
            coupure_str = str(coupure)
            stock["cheques_vac"][coupure_str] = stock["cheques_vac"].get(coupure_str, 0) + qte
            log_entry["ajouts"][f"cheques_vac_{coupure}"] = f"+{qte}"

    # ── CHÈQUES ───────────────────────────────────────────────────
    detail_ch = donnees.get("detail_cheques", [])
    if isinstance(detail_ch, list):
        for ch in detail_ch:
            if isinstance(ch, dict) and ch.get("montant", 0) > 0:
                # Cherche "numero" d'abord, puis "num" en fallback
                num = ch.get("numero") or ch.get("num")
                if not num:
                    continue

                existe = any(c.get("num") == num for c in stock["cheques"])
                if not existe:
                    stock["cheques"].append({
                        "num": num,
                        "montant": to_float(ch["montant"]) or 0.0,
                        "caisse": num_caisse,
                        "date": date_caisse
                    })
                    log_entry["ajouts"][f"cheque_{num}"] = ch["montant"]

    # ── ANCV ──────────────────────────────────────────────────────
    ancv_data = donnees.get("ancv_connect", {})
    if isinstance(ancv_data, dict):
        ancv_montant = to_float(ancv_data.get("total")) or 0.0
        if ancv_montant > 0:
            stock["ancv"]["total"] = stock["ancv"].get("total", 0.0) + ancv_montant
            log_entry["ajouts"]["ancv"] = f"+{ancv_montant}"

    # ✅ SAUVEGARDE
    stock["derniere_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    stock["historique"].append(log_entry)
    _sauvegarder(stock)

    logger.info(f"✅ Stock alimenté : {log_entry['ajouts']}")


# ══════════════════════════════════════════════════════════════════════════════
# LECTURE STOCK
# ══════════════════════════════════════════════════════════════════════════════

def get_stock() -> dict:
    """Retourne le stock complet."""
    return _charger()


def get_total_especes() -> float:
    """Retourne le total des espèces en €."""
    stock = _charger()
    return sum(
        float(coupure) * qte
        for coupure, qte in stock["especes"].items()
        if qte > 0
    )


def get_total_cheques_vac() -> float:
    """Retourne le total des chèques vacances en €."""
    stock = _charger()
    return sum(
        float(coupure) * qte
        for coupure, qte in stock["cheques_vac"].items()
        if qte > 0
    )


def get_total_cheques() -> float:
    """Retourne le total des chèques en €."""
    stock = _charger()
    return sum(to_float(ch.get("montant")) or 0.0 for ch in stock["cheques"])


def get_total_ancv() -> float:
    """Retourne le total ANCV en €."""
    return to_float(_charger()["ancv"].get("total")) or 0.0


def get_total_general() -> float:
    """Retourne le total général (toutes les remises)."""
    return (get_total_especes() +
            get_total_cheques_vac() +
            get_total_cheques() +
            get_total_ancv())


# ══════════════════════════════════════════════════════════════════════════════
# DÉCRÉMENTATION LORS D'UNE REMISE
# ══════════════════════════════════════════════════════════════════════════════

def retirer_remise(type_remise: str, detail: dict):
    """
    Appelé quand on valide une remise.
    Décrémente le stock du montant remis.

    Args:
        type_remise: "especes", "cheques_vac", "cheques" ou "ancv"
        detail: Dict contenant les billets/chèques remis
    """
    stock = _charger()

    if type_remise == "especes":
        for coupure, info in detail.get("billets", {}).items():
            qte = info.get("quantite", 0) if isinstance(info, dict) else 0
            coupure_str = str(coupure)
            stock["especes"][coupure_str] = max(
                0, stock["especes"].get(coupure_str, 0) - qte
            )
        logger.info(f"✅ Stock décrémenté espèces")

    elif type_remise == "cheques_vac":
        for coupure, info in detail.get("billets", {}).items():
            qte = info.get("quantite", 0) if isinstance(info, dict) else 0
            coupure_str = str(coupure)
            stock["cheques_vac"][coupure_str] = max(
                0, stock["cheques_vac"].get(coupure_str, 0) - qte
            )
        logger.info(f"✅ Stock décrémenté chèques vacances")

    elif type_remise == "cheques":
        nums_remis = {ch.get("num") for ch in detail.get("cheques", [])}
        stock["cheques"] = [
            ch for ch in stock["cheques"]
            if ch.get("num") not in nums_remis
        ]
        logger.info(f"✅ Stock décrémenté chèques : {len(nums_remis)} chèque(s)")

    elif type_remise == "ancv":
        montant = to_float(detail.get("total")) or 0.0
        stock["ancv"]["total"] = max(0.0, stock["ancv"]["total"] - montant)
        logger.info(f"✅ Stock décrémenté ANCV : {montant}€")

    stock["derniere_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _sauvegarder(stock)


# ══════════════════════════════════════════════════════════════════════════════
# MODIFICATION DIRECTE
# ══════════════════════════════════════════════════════════════════════════════

def modifier_stock_direct(changes: dict):
    """
    Modifie le stock directement (pour les échanges pièces ↔ billets).

    Args:
        changes: Dict avec clé "especes":
                 {"2": -2, "1": +5, ...}  (delta négatif = retire, positif = ajoute)

    Raises:
        ValueError: Si pas assez de stock pour retirer
    """
    stock = _charger()

    if "especes" in changes:
        for coupure, delta in changes["especes"].items():
            coupure_str = str(coupure)
            current = stock["especes"].get(coupure_str, 0)
            new_val = current + delta

            if new_val < 0:
                raise ValueError(
                    f"❌ Pas assez de {coupure}€ en stock! "
                    f"(actuellement: {current}, demandé: {delta})"
                )

            stock["especes"][coupure_str] = new_val
            logger.info(f"Échange: {coupure}€ → {current} → {new_val}")

    stock["derniere_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _sauvegarder(stock)
    logger.info(f"✅ Stock sauvegardé après échange")


# ══════════════════════════════════════════════════════════════════════════════
# RESET / SAUVEGARDE DIRECTE
# ══════════════════════════════════════════════════════════════════════════════

def reset_stock():
    """⚠️ Réinitialise le stock à zéro (test uniquement)."""
    _sauvegarder(_stock_vide())
    logger.warning("⚠️ Stock réinitialisé manuellement")


def sauvegarder_stock(stock: dict):
    """Sauvegarde le stock directement."""
    _sauvegarder(stock)


__all__ = [
    "alimenter_depuis_caisse",
    "get_stock",
    "get_total_especes",
    "get_total_cheques_vac",
    "get_total_cheques",
    "get_total_ancv",
    "get_total_general",
    "retirer_remise",
    "modifier_stock_direct",
    "reset_stock",
    "sauvegarder_stock",
]
