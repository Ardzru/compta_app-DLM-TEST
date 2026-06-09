# modules/module_3/lecteur_caisse.py
"""
Lecteur des fichiers caisse XLSM.
Centralise l'extraction des montants et détails depuis les feuilles de caisse.
"""

import openpyxl
from pathlib import Path
import logging
import re
from openpyxl.utils import coordinate_to_tuple

from config import CAISSES_MOIS_FR
from core import settings_manager
from core.utils.montant import to_float

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION DOSSIERS
# ══════════════════════════════════════════════════════════════════════════════

def trouver_dossier_jour(date, chemin_saison: str | None = None) -> str | None:
    """
    Trouve le dossier jour correspondant à une date.

    Args:
        date: Date (datetime.date)
        chemin_saison: Chemin saison optionnel

    Returns:
        Chemin du dossier jour ou None si introuvable
    """
    if chemin_saison is None:
        saison = settings_manager.get_saison_pour_date(date)
        if saison is None:
            saison = settings_manager.get_saison_active()
            logger.warning(
                f"Aucune saison ne couvre {date}, fallback sur '{saison['nom']}'"
            )
        chemin_saison = saison["chemin"]

    mois_str = f"{CAISSES_MOIS_FR[date.month]} {date.year}"
    # Teste les deux formats : "07" et "7"
    for jour_str in [str(date.day).zfill(2), str(date.day)]:
        chemin = Path(chemin_saison) / mois_str / jour_str
        if chemin.exists():
            logger.debug(f"Dossier trouvé : {chemin}")
            return str(chemin)

    logger.warning(f"Dossier introuvable pour {date} dans {chemin_saison}")
    return None


def lister_caisses(dossier_jour: str) -> list[str]:
    """
    Liste tous les fichiers caisses (.xlsm) d'un dossier jour.

    Args:
        dossier_jour: Chemin du dossier jour

    Returns:
        Liste triée des chemins de fichiers caisses
    """
    fichiers = sorted(Path(dossier_jour).glob("Caisse *.xlsm"))
    logger.debug(f"{len(fichiers)} caisse(s) trouvée(s) dans {dossier_jour}")
    return [str(f) for f in fichiers]


def extraire_numero_caisse(chemin_fichier: str) -> str:
    """
    Extrait le numéro de caisse depuis le nom du fichier.

    Args:
        chemin_fichier: Chemin du fichier (ex: "Caisse 01.xlsm")

    Returns:
        Numéro de caisse (ex: "01")
    """
    return Path(chemin_fichier).stem.replace("Caisse ", "").strip()


# ══════════════════════════════════════════════════════════════════════════════
# LECTURE FICHIER
# ══════════════════════════════════════════════════════════════════════════════

def lire_montants_caisse(chemin_fichier: str) -> dict:
    """
    Lit un fichier caisse XLSM et extrait tous les montants.

    Args:
        chemin_fichier: Chemin du fichier XLSM

    Returns:
        Dict avec structure :
        {
            "especes_bande": 123.45,
            "cb_sans_contact": 45.67,
            "detail_especes": {500: {"quantite": 2, "montant": 1000}, ...},
            "detail_cheques_vac": [{"numero": "CHV123", "montant": 50}, ...],
            ...
        }
    """
    logger.info(f"[MODULE3][LECTEUR] Lecture caisse fichier={chemin_fichier}")
    try:
        wb = openpyxl.load_workbook(chemin_fichier, data_only=True, read_only=True)
        ws = wb.active

        # Construire la grille (row, col) → valeur
        grid = {}
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    try:
                        r, c = coordinate_to_tuple(cell.coordinate)
                        grid[(r, c)] = cell.value
                    except (ValueError, TypeError):
                        pass

        wb.close()
        return _parser_montants(grid)

    except (OSError, TypeError) as err:
        logger.error(f"Erreur lecture {chemin_fichier}: {err}")
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _normaliser(texte) -> str:
    """Normalise un texte : minuscules, espaces uniques, strip."""
    return re.sub(r'\s+', ' ', str(texte).lower().strip())


def _chercher_label_col1(grid: dict, label: str, col_valeur: int = 3) -> float:
    """
    Cherche un label en colonne 1 et retourne la valeur en colonne col_valeur.
    Fallback sur colonne 2 si col_valeur est vide.

    Args:
        grid: Grille (row, col) → valeur
        label: Label à chercher
        col_valeur: Colonne de la valeur (défaut: 3)

    Returns:
        Valeur convertie en float, 0.0 si non trouvée
    """
    label_norm = _normaliser(label)
    for (row, col), val in grid.items():
        if col != 1:
            continue
        if _normaliser(val) == label_norm:
            # Colonne col_valeur
            v = to_float(grid.get((row, col_valeur)))
            if v is not None and v != 0.0:
                return v
            # Fallback colonne 2
            v2 = to_float(grid.get((row, 2)))
            if v2 is not None and v2 != 0.0:
                return v2
            return 0.0
    return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# PARSING PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def _parser_montants(grid: dict) -> dict:
    """
    Parse la grille Excel et extrait tous les montants.

    Args:
        grid: Grille (row, col) → valeur

    Returns:
        Dict avec tous les montants et détails
    """
    ch = lambda label: _chercher_label_col1(grid, label, col_valeur=3)

    return {
        # ── Bandes de caisse (Axess) ──────────────────────────────────────
        "especes_bande":        ch("Espèces"),
        "cb_sans_contact":      ch("CB Sans contact"),
        "cb_visa":              ch("CB Visa"),
        "dcc_planet":           ch("DCC PLANET"),
        "amex":                 ch("AMEX"),
        "amex_sans_contact":    ch("AMEX Sans contact"),
        "telecolecte":          ch("TéléCollecte"),
        "ancv_connect":         ch("ANCV Connect"),
        "cheques_vac_bande":    ch("Cheques Vacances"),
        "bons_livraisons":      ch("Bons de Livraisons"),
        "cheques_bande":        ch("Cheques"),
        "paiement_web":         ch("Paiement Web"),
        "virement":             ch("Virement"),
        "cb_vad":               ch("CB VAD"),
        "total_bandes":         ch("Total Bandes"),
        "total_paiements":      ch("Total Paiements"),

        # ── Écarts ────────────────────────────────────────────────────────
        "erreur_caisse":        ch("Erreur de Caisse"),
        "surplus_cheques_vac":  _lire_surplus_cheques_vac(grid),

        # ── Détails comptage ──────────────────────────────────────────────
        "total_especes_compte": _lire_total_especes_compte(grid),
        "detail_especes":       _lire_detail_especes(grid),
        "detail_cheques_vac":   _lire_detail_cheques_vac(grid),
        "detail_ancv":          _lire_detail_ancv(grid),
        "detail_cheques":       _lire_detail_cheques(grid),
    }


# ══════════════════════════════════════════════════════════════════════════════
# LECTURES SPÉCIFIQUES
# ══════════════════════════════════════════════════════════════════════════════

def _lire_surplus_cheques_vac(grid: dict) -> float:
    """Lit le surplus de chèques vacances."""
    for (row, col), val in grid.items():
        if col == 1 and _normaliser(val) == _normaliser("Surplus Chèques Vacances"):
            for c in range(2, 8):
                v = to_float(grid.get((row, c)))
                if v is not None:
                    return v
            return 0.0
    return 0.0


def _lire_total_especes_compte(grid: dict) -> float:
    """Lit le total des espèces comptées."""
    for (row, col), val in grid.items():
        if col == 11 and "total" in _normaliser(val) and "esp" in _normaliser(val):
            v = to_float(grid.get((row, 13)))
            if v is not None:
                return v
    return 0.0


def _lire_detail_especes(grid: dict) -> dict:
    """
    Lit le détail des espèces (billets et pièces).

    Returns:
        Dict {denomination: {"quantite": int, "montant": float}, ...}
    """
    valeurs_connues = {500, 200, 100, 50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01}
    result = {}

    header_row = None
    for (row, col), val in grid.items():
        if col == 11 and "billet" in _normaliser(val):
            header_row = row
            break

    if header_row is None:
        logger.debug("En-tête Billet/Pièce non trouvé")
        return result

    for (row, col), val in grid.items():
        if col != 11 or row <= header_row:
            continue

        fval = to_float(val)
        if fval is None or fval not in valeurs_connues:
            continue

        qte     = to_float(grid.get((row, 12))) or 0
        montant = to_float(grid.get((row, 13))) or 0.0

        result[fval] = {
            "quantite": int(qte),
            "montant":  montant,
        }

    return result


def _lire_detail_cheques_vac(grid: dict) -> list[dict]:
    """
    Lit le détail des chèques vacances.

    Returns:
        List [{"numero": str, "montant": float}, ...]
    """
    result = []

    header_row = None
    total_row  = None
    for (row, col), val in grid.items():
        if col == 15:
            n = _normaliser(val)
            if "num" in n and "ch" in n:
                header_row = row
            elif n == "total":
                total_row = row

    if header_row is None:
        logger.debug("En-tête numéro de chèque vacances non trouvé")
        return result

    for (row, col), val in grid.items():
        if col != 15 or row <= header_row:
            continue
        if total_row and row >= total_row:
            continue

        sv = str(val).strip()
        if not sv:
            continue

        montant = to_float(grid.get((row, 16))) or 0.0

        result.append({
            "numero":  sv,
            "montant": montant,
        })

    return result


def _lire_detail_ancv(grid: dict) -> list[dict]:
    """
    Cherche un tableau ANCV Connect dans le fichier.
    Format attendu : date | heure | montant sur colonnes consécutives.

    Returns:
        List [{"date": str, "heure": str, "montant": float}, ...]
    """
    result = []

    header_row = None
    ancv_col   = None
    for (row, col), val in grid.items():
        n = _normaliser(val)
        if "ancv" in n and "connect" in n:
            header_row = row
            ancv_col   = col
            break

    if header_row is None:
        logger.debug("En-tête ANCV Connect non trouvé")
        return result

    for r in range(header_row + 1, header_row + 200):
        val_c1 = grid.get((r, ancv_col))
        val_c2 = grid.get((r, ancv_col + 1))
        val_c3 = grid.get((r, ancv_col + 2))

        if val_c1 is None and val_c3 is None:
            continue

        montant = to_float(val_c3) or to_float(val_c2)
        if montant is None or montant == 0:
            continue

        result.append({
            "date":    str(val_c1).strip() if val_c1 else "",
            "heure":   str(val_c2).strip() if val_c2 else "",
            "montant": montant,
        })

    return result


def _lire_detail_cheques(grid: dict) -> list[dict]:
    """
    Cherche un tableau Chèques dans le fichier.
    Format attendu : numéro chèque | montant
    Ignore les chèques vacances (qui ont leur propre en-tête).

    Returns:
        List [{"numero": str, "montant": float}, ...]
    """
    result = []

    header_row  = None
    cheque_col  = None
    for (row, col), val in grid.items():
        n = _normaliser(val)
        if ("num" in n or "n°" in n) and "ch" in n and "vac" not in n:
            header_row = row
            cheque_col = col
            break

    if header_row is None:
        logger.debug("En-tête Chèques non trouvé")
        return result

    for r in range(header_row + 1, header_row + 200):
        val_num = grid.get((r, cheque_col))
        val_mnt = grid.get((r, cheque_col + 1))

        if val_num is None:
            continue

        sv = str(val_num).strip()
        if not sv or _normaliser(sv) == "total":
            break

        montant = to_float(val_mnt) or 0.0
        result.append({
            "numero":  sv,
            "montant": montant,
        })

    return result


__all__ = [
    "trouver_dossier_jour",
    "lister_caisses",
    "extraire_numero_caisse",
    "lire_montants_caisse",
]
