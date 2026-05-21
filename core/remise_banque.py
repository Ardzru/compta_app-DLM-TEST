# ═══════════════════════════════════════════════════════════════════════════════
# FILE: core/remises.py — COMPLET CORRIGÉ
# ═══════════════════════════════════════════════════════════════════════════════

import json
import logging
from pathlib import Path
from datetime import datetime
from core import stock as stock_module

logger = logging.getLogger(__name__)

REMISES_FILE = Path("data/remises.json")

def _charger() -> list:
    """Charge l'historique des remises depuis le fichier JSON."""
    if not REMISES_FILE.exists():
        REMISES_FILE.parent.mkdir(parents=True, exist_ok=True)
        return []
    try:
        data = json.loads(REMISES_FILE.read_text(encoding="utf-8"))
        logger.debug(f"✅ {len(data)} remises chargées")
        return data
    except Exception as e:
        logger.error(f"❌ Erreur lecture remises.json : {e}")
        return []

def _sauvegarder(data: list):
    """Sauvegarde l'historique des remises."""
    try:
        REMISES_FILE.parent.mkdir(parents=True, exist_ok=True)
        REMISES_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"✅ Remises sauvegardées : {REMISES_FILE}")
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde remises.json : {e}")

# ─── Ajout / Modification ──────────────────────────────────────────
def ajouter_remise(
        date_caisse: str,  # "2026-05-13"
        num_caisse: str,  # "60"
        type_remise: str,  # "especes" | "cheques_vac" | "cheques" | "ancv"
        detail: dict,  # {"billets": {...}, "total": 1610.56}
        remis_banque: bool = False
) -> int:
    """
    Ajoute une remise et retourne son ID.

    detail doit contenir:
    - Pour especes: {"billets": {"500": 5, ...}, "total": ...}
    - Pour cheques_vac: {"coupures": {"50": 2, ...}, "total": ...}
    - Pour cheques: {"cheques": [{"num": "123", "montant": 150}, ...], "total": ...}
    - Pour ancv: {"total": 200.0}
    """
    data = _charger()

    remise_id = max([r["id"] for r in data], default=0) + 1

    # ✅ CALCULER LE MONTANT TOTAL
    montant_total = 0.0

    if type_remise in ["especes", "cheques_vac"]:
        # Billets/coupures
        for coupure, info in detail.get("billets", {}).items():
            if isinstance(info, dict):
                qte = info.get("quantite", 0)
                montant = info.get("montant", 0.0)
                montant_total += montant
            else:
                # Si c'est juste un nombre
                montant_total += float(coupure) * int(info)

    elif type_remise == "cheques":
        # Chèques
        for ch in detail.get("cheques", []):
            montant_total += ch.get("montant", 0.0)

    elif type_remise == "ancv":
        montant_total = detail.get("total", 0.0)

    # Si le detail a un "total" au top niveau, l'utiliser comme fallback
    if montant_total == 0.0 and "total" in detail:
        montant_total = detail.get("total", 0.0)

    print(f"🔍 [DEBUG ajouter_remise] type={type_remise}, montant_total={montant_total}")

    nouvelle_remise = {
        "id": remise_id,
        "date_caisse": str(date_caisse),
        "num_caisse": str(num_caisse),
        "type": str(type_remise),
        "montant_total": round(montant_total, 2),  # ✅ AJOUTÉ!
        "detail": detail,
        "remis_banque": bool(remis_banque),
        "date_remise": None,
        "cree_le": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "valide_stock": False,
    }

    data.append(nouvelle_remise)
    _sauvegarder(data)

    logger.info(f"✅ Remise #{remise_id} ajoutée")
    logger.info(f"   📍 Caisse: {num_caisse}")
    logger.info(f"   📋 Type: {type_remise}")
    logger.info(f"   💰 Montant: {montant_total}€")

    return remise_id

def marquer_remis(remise_id: int):
    """Marque une remise comme remise à la banque."""
    data = _charger()
    trouve = False

    for r in data:
        if r["id"] == remise_id:
            r["remis_banque"] = True
            r["date_remise"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            trouve = True
            logger.info(f"✅ Remise #{remise_id} marquée comme remise à la banque")
            break

    if trouve:
        _sauvegarder(data)
    else:
        logger.warning(f"⚠️ Remise #{remise_id} introuvable")

def valider_remise_stock(remise_id: int) -> bool:
    """
    Valide une remise et déduit le stock.
    Retourne True si succès.
    """
    data = _charger()
    remise = None

    for r in data:
        if r["id"] == remise_id:
            remise = r
            break

    if not remise:
        logger.error(f"❌ Remise #{remise_id} introuvable")
        return False

    if remise.get("valide_stock"):
        logger.warning(f"⚠️ Remise #{remise_id} déjà validée")
        return False

    type_remise = remise["type"]
    detail = remise["detail"]

    logger.info(f"🔄 Validation stock remise #{remise_id} ({type_remise})")

    try:
        # Déduit du stock selon le type
        if type_remise == "especes":
            stock_module.decrementer_stock_remise(
                type_remise="especes",
                detail={
                    "total": remise.get("montant_total", 0.0),
                    "billets": detail.get("billets", {}),
                }
            )

        elif type_remise == "cheques_vac":
            stock_module.decrementer_stock_remise(
                type_remise="cheques_vac",
                detail={
                    "total": remise.get("montant_total", 0.0),
                    "coupures": detail.get("coupures", {}),
                }
            )

        elif type_remise == "cheques":
            stock_module.decrementer_stock_remise(
                type_remise="cheques",
                detail={
                    "total": remise.get("montant_total", 0.0),
                    "cheques": detail.get("cheques", []),
                }
            )

        elif type_remise == "ancv":
            stock_module.decrementer_stock_remise(
                type_remise="ancv",
                detail={
                    "total": remise.get("montant_total", 0.0),
                }
            )

        # Marque comme validée
        remise["valide_stock"] = True
        _sauvegarder(data)

        logger.info(f"✅ Remise #{remise_id} validée et stock déduit")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur validation remise #{remise_id} : {e}")
        return False

# ─── Getters ──────────────────────────────────────────────────────
def get_remise(remise_id: int) -> dict:
    """Récupère une remise par ID."""
    for r in _charger():
        if r["id"] == remise_id:
            return r
    return None

def get_remises_en_attente() -> list:
    """Retourne toutes les remises non validées au stock."""
    return [
        r for r in _charger()
        if not r.get("valide_stock", False)
    ]

def get_remises_non_remises_banque() -> list:
    """Retourne toutes les remises non remises à la banque."""
    return [
        r for r in _charger()
        if not r.get("remis_banque", False)
    ]

def get_remises_par_caisse(num_caisse: str) -> list:
    """Retourne toutes les remises d'une caisse."""
    return [
        r for r in _charger()
        if str(r.get("num_caisse")) == str(num_caisse)
    ]

def get_remises_par_type(type_remise: str) -> list:
    """Retourne toutes les remises d'un type donné."""
    return [
        r for r in _charger()
        if r.get("type") == type_remise
    ]

def get_remises_par_date(date_caisse: str) -> list:
    """Retourne toutes les remises d'une date donnée."""
    return [
        r for r in _charger()
        if r.get("date_caisse") == date_caisse
    ]

def get_historique(nb_entrees: int = 100) -> list:
    """Retourne les N dernières remises."""
    data = _charger()
    return data[-nb_entrees:] if len(data) > nb_entrees else data

def get_stats_remises() -> dict:
    """Retourne des statistiques sur les remises."""
    data = _charger()

    total_par_type = {}
    remises_en_attente = 0
    remises_stock_validees = 0
    remises_banque = 0

    for r in data:
        type_r = r.get("type", "?")
        montant = r.get("montant_total", 0.0)  # ✅ Utiliser montant_total

        if type_r not in total_par_type:
            total_par_type[type_r] = 0.0
        total_par_type[type_r] += montant

        if not r.get("valide_stock", False):
            remises_en_attente += 1
        else:
            remises_stock_validees += 1

        if r.get("remis_banque", False):
            remises_banque += 1

    return {
        "total_remises": len(data),
        "remises_en_attente_stock": remises_en_attente,
        "remises_stock_validees": remises_stock_validees,
        "remises_banque": remises_banque,
        "total_par_type": total_par_type,
        "total_general": sum(total_par_type.values()),
    }

# ─── Suppression / Reset ───────────────────────────────────────────
def supprimer_remise(remise_id: int) -> bool:
    """Supprime une remise (attention: irréversible)."""
    data = _charger()
    avant = len(data)

    data = [r for r in data if r["id"] != remise_id]

    if len(data) < avant:
        _sauvegarder(data)
        logger.warning(f"⚠️ Remise #{remise_id} supprimée")
        return True
    else:
        logger.warning(f"⚠️ Remise #{remise_id} introuvable")
        return False

def reset_remises():
    """Réinitialise l'historique des remises."""
    _sauvegarder([])
    logger.warning("⚠️ Historique des remises réinitialisé")
