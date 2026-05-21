"""
Gestion centralisée des paramètres de l'application.
Lit/écrit settings.json à la racine du projet.
"""
import json
from pathlib import Path
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

# Chemin du settings.json (racine projet, à côté de config.py)
SETTINGS_FILE = Path(__file__).parent.parent / "settings.json"

_cache: dict | None = None


# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT / SAUVEGARDE
# ══════════════════════════════════════════════════════════════════════════════

def _charger() -> dict:
    """Charge settings.json (avec cache mémoire)."""
    global _cache
    if _cache is None:
        if not SETTINGS_FILE.exists():
            logger.error(f"settings.json introuvable : {SETTINGS_FILE}")
            raise FileNotFoundError(
                f"settings.json manquant : {SETTINGS_FILE}\n"
                f"Créez ce fichier à la racine du projet."
            )
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            _cache = json.load(f)
        logger.debug(f"settings.json chargé depuis {SETTINGS_FILE}")
    return _cache


def _sauvegarder():
    """Réécrit settings.json sur disque."""
    global _cache
    if _cache is None:
        return
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(_cache, f, ensure_ascii=False, indent=2)
    logger.debug("settings.json sauvegardé")


def recharger():
    """Force le rechargement depuis le disque (utile si édition externe)."""
    global _cache
    _cache = None
    _charger()


# ══════════════════════════════════════════════════════════════════════════════
# SAISONS
# ══════════════════════════════════════════════════════════════════════════════

def lister_saisons() -> list[dict]:
    """Retourne la liste complète des saisons définies."""
    return _charger()["caisses"]["saisons"]


def get_noms_saisons() -> list[str]:
    """Retourne uniquement les noms des saisons (pour un menu déroulant)."""
    return [s["nom"] for s in lister_saisons()]


def get_saison_active() -> dict:
    """
    Retourne la saison active (définie dans settings.json).
    Lève une erreur si la saison active n'existe pas dans la liste.
    """
    cfg     = _charger()
    nom_act = cfg["caisses"]["saison_active"]
    for s in cfg["caisses"]["saisons"]:
        if s["nom"] == nom_act:
            return s
    # Fallback : première saison de la liste
    logger.warning(
        f"Saison active '{nom_act}' introuvable dans la liste, "
        f"fallback sur la première saison."
    )
    return cfg["caisses"]["saisons"][0]


def set_saison_active(nom: str):
    """
    Définit la saison active dans settings.json.
    Lève ValueError si le nom n'existe pas.
    """
    cfg = _charger()
    noms = [s["nom"] for s in cfg["caisses"]["saisons"]]
    if nom not in noms:
        raise ValueError(f"Saison '{nom}' inconnue. Saisons disponibles : {noms}")
    cfg["caisses"]["saison_active"] = nom
    _sauvegarder()
    logger.info(f"Saison active → '{nom}'")


def get_saison_pour_date(d: date) -> dict | None:
    """
    Retourne la saison qui couvre la date donnée.
    Retourne None si aucune saison ne correspond.
    """
    for saison in lister_saisons():
        try:
            debut = datetime.strptime(saison["date_debut"], "%Y-%m-%d").date()
            fin   = datetime.strptime(saison["date_fin"],   "%Y-%m-%d").date()
            if debut <= d <= fin:
                logger.debug(f"Date {d} → saison '{saison['nom']}'")
                return saison
        except (KeyError, ValueError) as e:
            logger.warning(f"Erreur parsing dates saison '{saison.get('nom')}': {e}")
            continue
    logger.debug(f"Aucune saison ne couvre la date {d}")
    return None


def ajouter_saison(nom: str, date_debut: str, date_fin: str, chemin: str):
    """
    Ajoute une nouvelle saison dans settings.json.
    date_debut / date_fin au format 'YYYY-MM-DD'.
    Lève ValueError si le nom existe déjà.
    """
    cfg  = _charger()
    noms = [s["nom"] for s in cfg["caisses"]["saisons"]]
    if nom in noms:
        raise ValueError(f"La saison '{nom}' existe déjà.")
    cfg["caisses"]["saisons"].append({
        "nom":        nom,
        "date_debut": date_debut,
        "date_fin":   date_fin,
        "chemin":     chemin,
    })
    _sauvegarder()
    logger.info(f"Saison ajoutée : '{nom}'")


def supprimer_saison(nom: str):
    """
    Supprime une saison de settings.json.
    Interdit de supprimer la saison active.
    """
    cfg = _charger()
    if cfg["caisses"]["saison_active"] == nom:
        raise ValueError(f"Impossible de supprimer la saison active '{nom}'.")
    avant = len(cfg["caisses"]["saisons"])
    cfg["caisses"]["saisons"] = [
        s for s in cfg["caisses"]["saisons"] if s["nom"] != nom
    ]
    if len(cfg["caisses"]["saisons"]) == avant:
        raise ValueError(f"Saison '{nom}' introuvable.")
    _sauvegarder()
    logger.info(f"Saison supprimée : '{nom}'")


# ══════════════════════════════════════════════════════════════════════════════
# CHEMINS
# ══════════════════════════════════════════════════════════════════════════════

def get_chemin_saison_active() -> Path:
    """Retourne le chemin réseau de la saison active."""
    return Path(get_saison_active()["chemin"])


def get_chemin_saison_pour_date(d: date) -> Path | None:
    """Retourne le chemin réseau de la saison couvrant la date, ou None."""
    saison = get_saison_pour_date(d)
    if saison is None:
        return None
    return Path(saison["chemin"])


# ══════════════════════════════════════════════════════════════════════════════
# INFOS GÉNÉRALES
# ══════════════════════════════════════════════════════════════════════════════

def get_societe() -> str:
    return _charger().get("societe", "")
