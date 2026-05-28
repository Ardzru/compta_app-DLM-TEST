# modules/module_3/stock.py
"""
Gestion du stock de remises (espèces, chèques, ANCV, etc.)
Persiste en JSON et permet les modifications/requêtes.
"""

import json
from pathlib import Path
from datetime import datetime
from config import logger
from core.utils.montant import to_float, format_montant

STOCK_FILE = Path("data/stock.json")

# ─── Structure stock ───────────────────────────────────────────────
# {
#   "especes":     {"200": 5, "100": 3, ...},   ← quantités par coupure
#   "cheques_vac": {"50": 2, "25": 8, ...},
#   "cheques":     [{"num": "1234567", "montant": 150.0, "caisse": "1", "date": "2026-05-20"}, ...],
#   "ancv":        {"total": 320.0},
#   "derniere_maj": "2026-05-13 15:08",
#   "historique":  [...]   ← log des alimentations
# }

# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES PRIVÉS
# ══════════════════════════════════════════════════════════════════════════════

def _charger() -> dict:
    """
    Charge le stock depuis le fichier JSON.

    Returns:
        dict: Stock complet ou stock vide si erreur

    Raises:
        Aucune — logs l'erreur et retourne stock vide
    """
    if not STOCK_FILE.exists():
        logger.debug(f"Fichier stock introuvable, création : {STOCK_FILE}")
        STOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        return _stock_vide()
    try:
        data = json.loads(STOCK_FILE.read_text(encoding="utf-8"))
        logger.debug(f"✅ Stock chargé : {STOCK_FILE}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur JSON stock.json : {e}")
        return _stock_vide()
    except Exception as e:
        logger.error(f"❌ Erreur lecture stock.json : {e}")
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


def _sauvegarder(data: dict) -> bool:
    """
    Sauvegarde le stock dans le fichier JSON.

    Args:
        data (dict): Stock à sauvegarder

    Returns:
        bool: True si succès, False sinon
    """
    try:
        STOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        STOCK_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.debug(f"✅ Stock sauvegardé : {STOCK_FILE}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde stock.json : {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# ALIMENTATION DU STOCK (depuis les caisses)
# ═══════════════════════════════════════════════════════════════════════════════

def alimenter_depuis_caisse(
        num_caisse: str,
        date_caisse: str,
        donnees: dict
) -> bool:
    """
    Alimente le stock depuis une caisse.

    Args:
        num_caisse (str): Numéro de la caisse (ex: "1", "2")
        date_caisse (str): Date de la caisse (YYYY-MM-DD)
        donnees (dict): Dict avec clés:
            - detail_especes: {"200": {"quantite": 5, "montant": 1000}, ...}
            - detail_cheques_vac_coupures: {"50": {"quantite": 2, "montant": 100}, ...}
            - detail_cheques: [{"numero": "123", "montant": 150}, ...]  ← "numero" OU "num"
            - ancv_connect: {"total": 320.0}

    Returns:
        bool: True si succès, False sinon

    Exemple:
        alimenter_depuis_caisse(
            "1",
            "2026-05-20",
            {
                "detail_especes": {"100": {"quantite": 5, "montant": 500}},
                "ancv_connect": {"total": 320.0}
            }
        )
        → True
    """
    logger.info(f"=== ALIMENTATION STOCK depuis caisse {num_caisse} ({date_caisse}) ===")

    stock = _charger()
    log_entry = {
        "caisse": num_caisse,
        "date": date_caisse,
        "alimente_le": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ajouts": {}
    }

    # ── ESPÈCES ──────────────────────────────────────────────────
    detail_esp = donnees.get("detail_especes", {})
    if detail_esp:
        logger.debug(f"  Espèces : {detail_esp}")
        for coupure, info in detail_esp.items():
            qte = 0
            if isinstance(info, dict):
                qte = int(info.get("quantite", 0) or 0)

            if qte > 0:
                coupure_str = str(coupure)
                stock["especes"][coupure_str] = stock["especes"].get(coupure_str, 0) + qte
                log_entry["ajouts"][f"especes_{coupure}"] = f"+{qte}"
                logger.debug(f"    {coupure}€: +{qte} → {stock['especes'][coupure_str]} total")

    # ── CHÈQUES VACANCES ─────────────────────────────────────────
    detail_cv = donnees.get("detail_cheques_vac_coupures", {})
    if detail_cv:
        logger.debug(f"  Chèques Vac : {detail_cv}")
        for coupure, info in detail_cv.items():
            qte = 0
            if isinstance(info, dict):
                qte = int(info.get("quantite", 0) or 0)

            if qte > 0:
                coupure_str = str(coupure)
                stock["cheques_vac"][coupure_str] = stock["cheques_vac"].get(coupure_str, 0) + qte
                log_entry["ajouts"][f"cheques_vac_{coupure}"] = f"+{qte}"
                logger.debug(f"    {coupure}€: +{qte} → {stock['cheques_vac'][coupure_str]} total")

    # ── CHÈQUES ───────────────────────────────────────────────────
    detail_ch = donnees.get("detail_cheques", [])
    if isinstance(detail_ch, list) and detail_ch:
        logger.debug(f"  Chèques : {len(detail_ch)} chèque(s)")
        for ch in detail_ch:
            if isinstance(ch, dict):
                montant = to_float(ch.get("montant", 0))
                # ✅ Essaie "numero" d'abord, sinon "num"
                num = ch.get("numero") or ch.get("num")

                if montant > 0 and num:
                    existe = any(c.get("num") == str(num) for c in stock["cheques"])
                    if not existe:
                        stock["cheques"].append({
                            "num": str(num),
                            "montant": round(montant, 2),
                            "caisse": num_caisse,
                            "date": date_caisse
                        })
                        log_entry["ajouts"][f"cheque_{num}"] = format_montant(montant)
                        logger.debug(f"    Chèque {num}: +{format_montant(montant)}€")
                    else:
                        logger.warning(f"    ⚠️ Chèque {num} déjà en stock")

    # ── ANCV ──────────────────────────────────────────────────────
    ancv_data = donnees.get("ancv_connect", {})
    if isinstance(ancv_data, dict) and ancv_data:
        logger.debug(f"  ANCV : {ancv_data}")
        ancv_montant = to_float(ancv_data.get("total", 0))
        if ancv_montant > 0:
            ancien_total = to_float(stock["ancv"].get("total", 0))
            stock["ancv"]["total"] = round(ancien_total + ancv_montant, 2)
            log_entry["ajouts"]["ancv"] = f"+{format_montant(ancv_montant)}"
            logger.debug(f"    ANCV: +{format_montant(ancv_montant)}€ → {format_montant(stock['ancv']['total'])}€ total")

    # ✅ SAUVEGARDE
    stock["derniere_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    stock["historique"].append(log_entry)

    if _sauvegarder(stock):
        logger.info(f"✅ Stock alimenté depuis caisse {num_caisse}")
        for cle, val in log_entry["ajouts"].items():
            logger.info(f"   → {cle}: {val}")
        return True
    else:
        logger.error(f"❌ Impossible de sauvegarder le stock")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# LECTURE STOCK
# ═══════════════════════════════════════════════════════════════════════════════

def get_stock() -> dict:
    """
    Retourne le stock complet.

    Returns:
        dict: Stock avec structure complète

    Exemple:
        stock = get_stock()
        → {"especes": {"100": 5, ...}, "cheques": [...], ...}
    """
    return _charger()


def get_total_especes() -> float:
    """
    Retourne le total des espèces en €.

    Returns:
        float: Montant total (arrondi à 2 décimales)

    Exemple:
        get_total_especes()
        → 1250.50  (si 5×100€ + 2×25€ + 0.50€)
    """
    stock = _charger()
    total = 0.0
    for coupure_str, qte in stock.get("especes", {}).items():
        try:
            coupure = to_float(coupure_str)
            total += coupure * int(qte)
        except (ValueError, TypeError):
            logger.warning(f"Coupure espèce invalide : {coupure_str!r}")
            continue
    return round(total, 2)


def get_total_cheques_vac() -> float:
    """
    Retourne le total des chèques vacances en €.

    Returns:
        float: Montant total

    Exemple:
        get_total_cheques_vac()
        → 1350.00
    """
    stock = _charger()
    total = 0.0
    for coupure_str, qte in stock.get("cheques_vac", {}).items():
        try:
            coupure = to_float(coupure_str)
            total += coupure * int(qte)
        except (ValueError, TypeError):
            logger.warning(f"Coupure CV invalide : {coupure_str!r}")
            continue
    return round(total, 2)


def get_total_cheques() -> float:
    """
    Retourne le total des chèques en €.

    Returns:
        float: Montant total

    Exemple:
        get_total_cheques()
        → 750.00
    """
    stock = _charger()
    cheques = stock.get("cheques", [])
    total = sum(to_float(ch.get("montant", 0)) for ch in cheques)
    return round(total, 2)


def get_total_ancv() -> float:
    """
    Retourne le total ANCV en €.

    Returns:
        float: Montant total

    Exemple:
        get_total_ancv()
        → 320.00
    """
    stock = _charger()
    return round(to_float(stock.get("ancv", {}).get("total", 0)), 2)


def get_total_general() -> float:
    """
    Retourne le total général (toutes les remises).

    Returns:
        float: Somme de tous les stocks

    Exemple:
        get_total_general()
        → 3670.50  (1250.50 + 1350 + 750 + 320)
    """
    total = round(
        get_total_especes() +
        get_total_cheques_vac() +
        get_total_cheques() +
        get_total_ancv(),
        2
    )
    logger.debug(f"Total général stock : {format_montant(total)}€")
    return total

# ═══════════════════════════════════════════════════════════════════════════════
# DÉCRÉMENTATION LORS D'UNE REMISE
# ═══════════════════════════════════════════════════════════════════════════════

def retirer_remise(type_remise: str, detail: dict) -> bool:
    """
    Appelé quand on valide une remise banque.
    Décrémente le stock du montant remis.

    Args:
        type_remise (str): "especes", "cheques_vac", "cheques" ou "ancv"
        detail (dict): Dict contenant les billets/chèques remis

    Returns:
        bool: True si succès, False sinon

    Exemple:
        retirer_remise("especes", {"billets": {"100": {"quantite": 5}}})
        → True
    """
    logger.info(f"🔄 Retrait stock : {type_remise}")

    stock = _charger()

    if type_remise == "especes":
        billets = detail.get("billets", {})
        for coupure, info in billets.items():
            qte = int(info.get("quantite", 0) or 0) if isinstance(info, dict) else int(info)
            if qte > 0:
                coupure_str = str(coupure)
                ancien = stock["especes"].get(coupure_str, 0)
                nouveau = max(0, ancien - qte)
                stock["especes"][coupure_str] = nouveau
                logger.debug(f"  {coupure}€: {ancien} → {nouveau} (-{qte})")

    elif type_remise == "cheques_vac":
        billets = detail.get("billets", {}) or detail.get("coupures", {})
        for coupure, info in billets.items():
            qte = int(info.get("quantite", 0) or 0) if isinstance(info, dict) else int(info)
            if qte > 0:
                coupure_str = str(coupure)
                ancien = stock["cheques_vac"].get(coupure_str, 0)
                nouveau = max(0, ancien - qte)
                stock["cheques_vac"][coupure_str] = nouveau
                logger.debug(f"  {coupure}€: {ancien} → {nouveau} (-{qte})")

    elif type_remise == "cheques":
        cheques = detail.get("cheques", [])
        nums_remis = {str(ch.get("num") or ch.get("numero")) for ch in cheques}
        stock["cheques"] = [
            ch for ch in stock["cheques"]
            if ch.get("num") not in nums_remis
        ]
        logger.debug(f"  {len(nums_remis)} chèque(s) retirés")

    elif type_remise == "ancv":
        montant = to_float(detail.get("total", 0))
        ancien = to_float(stock["ancv"].get("total", 0))
        nouveau = max(0.0, round(ancien - montant, 2))
        stock["ancv"]["total"] = nouveau
        logger.debug(f"  ANCV: {format_montant(ancien)}€ → {format_montant(nouveau)}€ (-{format_montant(montant)}€)")

    # ✅ SAUVEGARDE
    stock["derniere_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    if _sauvegarder(stock):
        logger.info(f"✅ Stock décrémenté et sauvegardé ({type_remise})")
        return True
    else:
        logger.error(f"❌ Impossible de sauvegarder le stock")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# MODIFICATION DIRECTE (pour les échanges pièces ↔ billets)
# ═══════════════════════════════════════════════════════════════════════════════

def modifier_stock_direct(changes: dict) -> bool:
    """
    Modifie le stock directement (pour les échanges pièces ↔ billets).

    Args:
        changes (dict): Dict avec clé "especes":
                        {"2": -2, "1": +5, ...}
                        (delta négatif = retire, positif = ajoute)

    Returns:
        bool: True si succès, False sinon

    Raises:
        ValueError: Si pas assez de stock pour retirer

    Exemple:
        modifier_stock_direct({"especes": {"2": -2, "1": +5}})
        → True  (retire 2 pièces de 2€, ajoute 5 pièces de 1€)
    """
    stock = _charger()

    if "especes" in changes:
        for coupure, delta in changes["especes"].items():
            coupure_str = str(coupure)
            current = int(stock["especes"].get(coupure_str, 0))
            new_val = current + delta

            if new_val < 0:
                raise ValueError(
                    f"❌ Pas assez de {coupure}€ en stock! "
                    f"(actuellement: {current}, demandé: {delta:+d})"
                )

            stock["especes"][coupure_str] = new_val
            logger.info(
                f"  Échange {coupure}€: {current} → {new_val} (delta: {delta:+d})"
            )

    stock["derniere_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    if _sauvegarder(stock):
        logger.info(f"✅ Stock sauvegardé après échange")
        return True
    else:
        logger.error(f"❌ Impossible de sauvegarder le stock")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# RESET & ALIAS
# ═══════════════════════════════════════════════════════════════════════════════

def reset_stock() -> bool:
    """
    ⚠️ Réinitialise le stock à zéro (test uniquement).

    Returns:
        bool: True si succès, False sinon
    """
    if _sauvegarder(_stock_vide()):
        logger.warning("⚠️ Stock réinitialisé manuellement")
        return True
    return False


def sauvegarder_stock(stock: dict) -> bool:
    """
    Sauvegarde le stock directement.

    Args:
        stock (dict): Stock complet à sauvegarder

    Returns:
        bool: True si succès, False sinon
    """
    return _sauvegarder(stock)
