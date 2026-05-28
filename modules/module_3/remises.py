# modules/module_3/remises.py
"""
Gestion de l'historique des remises (espèces, chèques, ANCV, etc.)
Persiste en JSON et coordonne avec le stock.
"""

import json
from pathlib import Path
from datetime import datetime
from config import logger, DOSSIER_SAISIES
from core.utils.montant import to_float, format_montant

REMISES_FILE = DOSSIER_SAISIES / "remises.json"


# ──────────────────────────────────────────────────────────────────────────────
# UTILITAIRES PRIVÉS
# ──────────────────────────────────────────────────────────────────────────────

def _charger() -> list:
    """Charge l'historique des remises depuis le fichier JSON."""
    if not REMISES_FILE.exists():
        logger.debug(f"Fichier remises introuvable, création : {REMISES_FILE}")
        REMISES_FILE.parent.mkdir(parents=True, exist_ok=True)
        return []
    try:
        data = json.loads(REMISES_FILE.read_text(encoding="utf-8"))
        logger.debug(f"✅ {len(data)} remises chargées")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur JSON remises.json : {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Erreur lecture remises.json : {e}")
        return []


def _sauvegarder(data: list) -> bool:
    """Sauvegarde l'historique des remises."""
    try:
        REMISES_FILE.parent.mkdir(parents=True, exist_ok=True)
        REMISES_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.debug(f"✅ {len(data)} remises sauvegardées")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde remises.json : {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# AJOUT / MODIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def ajouter_remise(
        date_caisse: str,
        num_caisse: str,
        type_remise: str,
        detail: dict,
        remis_banque: bool = False
) -> int:
    """Ajoute une remise et retourne son ID."""
    data = _charger()
    remise_id = max([r.get("id", 0) for r in data], default=0) + 1

    montant_total = 0.0
    if type_remise == "especes":
        montant_total = sum(
            to_float(coupure) * to_float(detail.get(coupure, {}).get("quantite", 0))
            for coupure in detail
        )
    elif type_remise == "cheques_vac":
        montant_total = sum(
            to_float(coupure) * to_float(detail.get(coupure, {}).get("quantite", 0))
            for coupure in detail
        )
    elif type_remise == "cheques":
        montant_total = sum(ch.get("montant", 0.0) for ch in detail if isinstance(detail, list))
    elif type_remise == "ancv":
        montant_total = to_float(detail.get("montant", 0))

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
    logger.info(f"✅ Remise #{remise_id} ajoutée (Type: {type_remise}, Montant: {montant_total}€)")
    return remise_id


def marquer_remis(remise_id: int) -> bool:
    """Marque une remise comme remise à la banque."""
    data = _charger()
    for r in data:
        if r["id"] == remise_id:
            r["remis_banque"] = True
            r["date_remise"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            _sauvegarder(data)
            logger.info(f"✅ Remise #{remise_id} marquée comme remise à la banque")
            return True
    logger.warning(f"⚠️ Remise #{remise_id} introuvable")
    return False


def valider_remise_stock(remise_id: int) -> bool:
    """Valide une remise et déduit le stock."""
    data = _charger()
    for r in data:
        if r["id"] == remise_id:
            r["valide_stock"] = True
            _sauvegarder(data)
            logger.info(f"✅ Remise #{remise_id} validée en stock")
            return True
    logger.warning(f"⚠️ Remise #{remise_id} introuvable")
    return False


# ══════════════════════════════════════════════════════════════════════════════
# LECTURE
# ══════════════════════════════════════════════════════════════════════════════

def get_remise(remise_id: int) -> dict:
    """Récupère une remise par ID."""
    for r in _charger():
        if r["id"] == remise_id:
            return r
    return {}


def get_remises_en_attente() -> list:
    """Retourne toutes les remises en attente de validation stock."""
    return [r for r in _charger() if not r.get("valide_stock", False)]


def get_remises_non_remises_banque() -> list:
    """Retourne toutes les remises non remises à la banque."""
    return [r for r in _charger() if not r.get("remis_banque", False)]


def get_remises_par_caisse(num_caisse: str) -> list:
    """Retourne toutes les remises d'une caisse donnée."""
    return [r for r in _charger() if r.get("num_caisse") == num_caisse]


def get_remises_par_type(type_remise: str) -> list:
    """Retourne toutes les remises d'un type donné."""
    return [r for r in _charger() if r.get("type") == type_remise]


def get_remises_par_date(date_caisse: str) -> list:
    """Retourne toutes les remises d'une date donnée."""
    return [r for r in _charger() if r.get("date_caisse") == date_caisse]


def get_historique(nb_entrees: int = 100) -> list:
    """Retourne les N dernières remises."""
    data = _charger()
    return data[-nb_entrees:] if len(data) > nb_entrees else data


def get_stats_remises() -> dict:
    """Retourne des statistiques globales sur les remises."""
    data = _charger()
    total_par_type = {}
    remises_en_attente = 0
    remises_stock_validees = 0
    remises_banque = 0

    for r in data:
        type_r = r.get("type", "?")
        montant = to_float(r.get("montant_total", 0))
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
        "total_general": round(sum(total_par_type.values()), 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# SUPPRESSION / RESET
# ══════════════════════════════════════════════════════════════════════════════

def supprimer_remise(remise_id: int) -> bool:
    """Supprime une remise."""
    data = _charger()
    avant = len(data)
    data = [r for r in data if r["id"] != remise_id]
    if len(data) < avant:
        if _sauvegarder(data):
            logger.warning(f"⚠️ Remise #{remise_id} supprimée")
            return True
        else:
            logger.error(f"❌ Impossible de supprimer la remise #{remise_id}")
            return False
    else:
        logger.warning(f"⚠️ Remise #{remise_id} introuvable")
        return False


def reset_remises() -> bool:
    """Réinitialise l'historique des remises."""
    if _sauvegarder([]):
        logger.warning("⚠️ Historique des remises réinitialisé")
        return True
    return False
