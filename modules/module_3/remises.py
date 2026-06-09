# modules/module_3/remises.py
"""
Gestion des remises bancaires.
Historique, validation et export des remises (espèces, chèques, etc.).
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from core.utils.montant import to_float
from core.utils.fichiers import creer_dossier
from . import stock

logger = logging.getLogger(__name__)

REMISES_FILE = Path("data/remises.json")


# ══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════

def _charger() -> list:
    """Charge l'historique des remises depuis le fichier JSON."""
    if not REMISES_FILE.exists():
        creer_dossier(REMISES_FILE.parent)
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
        creer_dossier(REMISES_FILE.parent)
        REMISES_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"✅ Remises sauvegardées : {REMISES_FILE}")
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde remises.json : {e}")


# ══════════════════════════════════════════════════════════════════════════════
# AJOUT / MODIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def ajouter_remise(
        date_caisse: str,      # "2026-05-13"
        num_caisse: str,       # "60"
        type_remise: str,      # "especes" | "cheques_vac" | "cheques" | "ancv"
        detail: dict,          # Détails selon le type
        remis_banque: bool = False
) -> int:
    """
    Ajoute une remise et retourne son ID.

    Args:
        date_caisse: Date de la caisse (format YYYY-MM-DD)
        num_caisse: Numéro de la caisse
        type_remise: Type de remise
        detail: Dict contenant les données selon le type :
            - especes: {"billets": {"500": {"quantite": 5, "montant": 2500}, ...}, "total": ...}
            - cheques_vac: {"coupures": {"50": {"quantite": 2}, ...}, "total": ...}
            - cheques: {"cheques": [{"num": "123", "montant": 150}, ...], "total": ...}
            - ancv: {"total": 200.0}
        remis_banque: Si True, marque comme remis à la banque

    Returns:
        ID de la remise créée
    """
    data = _charger()
    remise_id = max([r["id"] for r in data], default=0) + 1

    # ── Calculer le montant total ──────────────────────────────
    montant_total = _calculer_montant_total(type_remise, detail)

    logger.debug(f"[REMISE] type={type_remise}, montant={montant_total}€")

    nouvelle_remise = {
        "id": remise_id,
        "date_caisse": str(date_caisse),
        "num_caisse": str(num_caisse),
        "type": str(type_remise),
        "montant_total": round(montant_total, 2),
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


def _calculer_montant_total(type_remise: str, detail: dict) -> float:
    """
    Calcule le montant total d'une remise selon son type.

    Args:
        type_remise: Type de remise
        detail: Dictionnaire de détail

    Returns:
        Montant total en euros
    """
    montant_total = 0.0

    if type_remise in ["especes", "cheques_vac"]:
        # Billets/coupures : {"500": {"quantite": 5, "montant": 2500}, ...}
        for coupure, info in detail.get("billets", {}).items():
            if isinstance(info, dict):
                montant_total += info.get("montant", 0.0)
            else:
                # Fallback si c'est juste un nombre
                montant_total += float(coupure) * int(info)

    elif type_remise == "cheques":
        # Chèques : [{"num": "123", "montant": 150}, ...]
        for ch in detail.get("cheques", []):
            montant_total += ch.get("montant", 0.0)

    elif type_remise == "ancv":
        montant_total = detail.get("total", 0.0)

    # Fallback si "total" au niveau racine du detail
    if montant_total == 0.0 and "total" in detail:
        montant_total = detail.get("total", 0.0)

    return to_float(montant_total) or 0.0


def marquer_remis(remise_id: int):
    """
    Marque une remise comme remise à la banque.

    Args:
        remise_id: ID de la remise
    """
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

    Args:
        remise_id: ID de la remise

    Returns:
        True si succès, False sinon
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
        # Décrémente du stock selon le type
        if type_remise == "especes":
            stock.retirer_remise(
                type_remise="especes",
                detail={
                    "total": remise.get("montant_total", 0.0),
                    "billets": detail.get("billets", {}),
                }
            )

        elif type_remise == "cheques_vac":
            stock.retirer_remise(
                type_remise="cheques_vac",
                detail={
                    "total": remise.get("montant_total", 0.0),
                    "billets": detail.get("coupures", {}),
                }
            )

        elif type_remise == "cheques":
            stock.retirer_remise(
                type_remise="cheques",
                detail={
                    "total": remise.get("montant_total", 0.0),
                    "cheques": detail.get("cheques", []),
                }
            )

        elif type_remise == "ancv":
            stock.retirer_remise(
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


# ══════════════════════════════════════════════════════════════════════════════
# GETTERS
# ══════════════════════════════════════════════════════════════════════════════

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
        montant = r.get("montant_total", 0.0)

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


# ══════════════════════════════════════════════════════════════════════════════
# SUPPRESSION / RESET
# ══════════════════════════════════════════════════════════════════════════════

def supprimer_remise(remise_id: int) -> bool:
    """Supprime une remise (irréversible)."""
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
    """⚠️ Réinitialise l'historique des remises."""
    _sauvegarder([])
    logger.warning("⚠️ Historique des remises réinitialisé")


__all__ = [
    "ajouter_remise",
    "marquer_remis",
    "valider_remise_stock",
    "get_remise",
    "get_remises_en_attente",
    "get_remises_non_remises_banque",
    "get_remises_par_caisse",
    "get_remises_par_type",
    "get_remises_par_date",
    "get_historique",
    "get_stats_remises",
    "supprimer_remise",
    "reset_remises",
]
