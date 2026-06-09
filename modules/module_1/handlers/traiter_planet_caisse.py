"""
Module 1 - Handler PLANET CAISSE
Traite les fichiers de transactions Planet Caisse (Instore/POS)
et génère les écritures comptables.

Compte transit : 580005
Libellé enrichi avec numéro de caisse via fichier de correspondance.
"""

from pathlib import Path
from collections import defaultdict
import openpyxl
import pandas as pd

from config import DOSSIER_SORTIE
from config import logger
from core.utils.montant import format_montant_compta
from core.utils.constantes import (
    STE_DLM,
    COMPTE_COMM,
    COMPTE_PRINCIPAL,
    JOURNAL_CEBOOBA,
    ANALYTIQUE_VIDE,
    AUX_PLANET,
    COL_STE, COL_DATE, COL_COMPTE, COL_AUX,
    COL_PIECE, COL_OBJET, COL_DEBIT, COL_CREDIT,
    COL_JOURNAL, COL_ANALYTIQUE,
    COLONNES_SORTIE,
    PLANET_COL,
)

# ==========================================================
# CONSTANTES SPÉCIFIQUES PLANET CAISSE
# ==========================================================
COMPTE_TRANSIT_CAISSE = "580005"

# Chemin vers le fichier de correspondance caisse
FICHIER_CORRESPONDANCE_CAISSE = Path("config/correspondance_caisse.xlsx")

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotPlanetCaisseFileError(Exception):
    """Levée si le fichier Planet Caisse n'est pas exploitable."""
    pass

# ==========================================================
# COLONNES ATTENDUES (indices 0-based)
# ==========================================================
_COL_TYPE     = PLANET_COL["type"]      # 6
_COL_LOT      = PLANET_COL["lot"]       # 11
_COL_BRUT     = PLANET_COL["brut"]      # 13
_COL_DATE_TXN = PLANET_COL["date_txn"]  # 15
_COL_DATE_VAL = PLANET_COL["date_val_caisses"]  # 30
_COL_COMM     = PLANET_COL["comm"]      # 23
_COL_LIBEL    = PLANET_COL["libel"]     # 31
_COL_TVA      = PLANET_COL["tva"]       # 39

# ==========================================================
# UTILITAIRES INTERNES
# ==========================================================

def _formater_date(val) -> str:
    """Convertit une date au format JJ/MM/AAAA."""
    if val is None:
        return ""
    s = str(val).strip()
    if "-" in s:
        s = s[:10]
        try:
            y, m, d = s.split("-")
            return f"{d}/{m}/{y}"
        except ValueError:
            return s
    return s

def _date_cle(val) -> str:
    """Retourne une clé de date pour le tri (AAAAMMJJ)."""
    if val is None:
        return ""
    s = str(val).strip()
    if "-" in s:
        return s[:10].replace("-", "")
    parts = s.split("/")
    if len(parts) == 3:
        return parts[2] + parts[1] + parts[0]
    return s

def _to_float(val) -> float:
    """Convertit une valeur en float. Retourne 0.0 si non numérique."""
    try:
        return float(val) if val not in (None, "", "NA") else 0.0
    except (ValueError, TypeError):
        return 0.0

# ==========================================================
# CHARGEMENT DU FICHIER DE CORRESPONDANCE CAISSE
# ==========================================================

_cache_correspondance: dict | None = None

def _charger_correspondance_caisse() -> dict:
    """
    Charge le fichier de correspondance caisse depuis Excel.

    Format attendu :
    - Colonne A : identifiant (MID, terminal ID, lot, libellé…)
    - Colonne B : numéro de caisse

    Retourne un dict { identifiant_str: numero_caisse_str }
    """
    global _cache_correspondance
    if _cache_correspondance is not None:
        return _cache_correspondance

    _cache_correspondance = {}

    if not FICHIER_CORRESPONDANCE_CAISSE.exists():
        logger.warning(
            f"[PLANET CAISSE] Fichier de correspondance introuvable : "
            f"{FICHIER_CORRESPONDANCE_CAISSE}"
        )
        return _cache_correspondance

    try:
        df = pd.read_excel(
            FICHIER_CORRESPONDANCE_CAISSE,
            header=0,
            dtype=str,
        )
        if df.shape[1] < 2:
            logger.warning(
                "[PLANET CAISSE] Fichier de correspondance : "
                "moins de 2 colonnes, ignoré."
            )
            return _cache_correspondance

        col_id     = df.columns[0]
        col_caisse = df.columns[1]

        for _, row in df.iterrows():
            cle    = str(row[col_id]).strip()    if pd.notna(row[col_id])    else ""
            valeur = str(row[col_caisse]).strip() if pd.notna(row[col_caisse]) else ""
            if cle:
                _cache_correspondance[cle] = valeur

        logger.info(
            f"[PLANET CAISSE] Correspondances chargées : "
            f"{len(_cache_correspondance)} entrée(s)"
        )

    except Exception as e:
        logger.error(
            f"[PLANET CAISSE] Erreur chargement correspondance : {e}"
        )

    return _cache_correspondance


def _obtenir_numero_caisse(libel_brut: str, lot_id: str) -> str:
    """
    Cherche le numéro de caisse pour un libellé ou un lot donné.

    Stratégie (ordre) :
    1. Correspondance exacte sur le libellé brut
    2. Correspondance exacte sur le lot_id
    3. Correspondance partielle (clé contenue dans le libellé)

    Retourne le numéro de caisse ou "" si non trouvé.
    """
    correspondances = _charger_correspondance_caisse()
    if not correspondances:
        return ""

    # 1. Exacte sur libellé
    if libel_brut in correspondances:
        return correspondances[libel_brut]

    # 2. Exacte sur lot
    if lot_id in correspondances:
        return correspondances[lot_id]

    # 3. Partielle
    libel_upper = libel_brut.upper()
    for cle, valeur in correspondances.items():
        if cle and cle.upper() in libel_upper:
            return valeur

    return ""


def _construire_libelle(prefixe: str, date_txn: str, libel_brut: str, lot_id: str) -> str:
    """
    Construit le libellé enrichi avec numéro de caisse si disponible.

    Avec caisse    : "PLANET DU 01/01/2024 CAISSE 12"
    Sans caisse    : "PLANET DU 01/01/2024"
    """
    caisse = _obtenir_numero_caisse(libel_brut, lot_id)
    base   = f"{prefixe} {date_txn}"
    if caisse:
        return f"{base} CAISSE {caisse}"
    return base

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_planet_caisse(fichier: Path) -> tuple[str, str]:
    """
    Traite un fichier de transactions Planet Caisse (Instore/POS).

    Logique métier :
    - Regroupe les transactions par lot
    - Ventile Sales vs Refunds
    - Génère écritures brut + frais + net
    - Libellé enrichi avec numéro de caisse

    Retourne:
        ("OK", chemin_fichier) | ("ERREUR", message)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        msg = f"Fichier Planet Caisse introuvable : {fichier}"
        logger.error(f"[PLANET CAISSE] {msg}")
        return "ERREUR", msg

    logger.info(
        f"[MODULE1][PLANET CAISSE] Début traitement : {fichier.name}"
    )

    try:
        # ----------------------------------------------------------
        # 1. Lecture Excel
        # ----------------------------------------------------------
        try:
            wb = openpyxl.load_workbook(
                fichier, read_only=True, data_only=True
            )
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
        except Exception as e:
            msg = f"Impossible de lire {fichier.name} : {e}"
            logger.error(f"[PLANET CAISSE] {msg}")
            raise NotPlanetCaisseFileError(msg)

        if len(rows) < 2:
            msg = "Fichier vide ou sans données"
            logger.warning(f"[PLANET CAISSE] {msg}")
            raise NotPlanetCaisseFileError(msg)

        # ----------------------------------------------------------
        # 2. Lecture et regroupement par lot
        # ----------------------------------------------------------
        lots = defaultdict(lambda: {
            "Sale":     [],
            "Refund":   [],
            "date":     "",
            "date_cle": "",
            "date_txn": "",
            "libel":    "",
        })
        nb_ignores = 0

        max_col = max(
            _COL_TYPE, _COL_LOT, _COL_BRUT, _COL_DATE_TXN,
            _COL_DATE_VAL, _COL_COMM, _COL_LIBEL, _COL_TVA
        )

        for i, row in enumerate(rows[1:], start=2):
            if len(row) <= max_col:
                continue

            type_txn = str(row[_COL_TYPE]).strip() if row[_COL_TYPE] else ""

            if type_txn == "Declined Trx":
                nb_ignores += 1
                continue

            if type_txn not in ("Sale", "Refund"):
                continue

            lot_id   = str(row[_COL_LOT]).strip()    if row[_COL_LOT]      else ""
            brut     = _to_float(row[_COL_BRUT])
            comm     = _to_float(row[_COL_COMM])
            tva      = _to_float(row[_COL_TVA])
            libel    = str(row[_COL_LIBEL]).strip()  if row[_COL_LIBEL]    else ""
            date_txn = _formater_date(row[_COL_DATE_TXN])
            date_val = _formater_date(row[_COL_DATE_VAL])
            dcle     = _date_cle(row[_COL_DATE_VAL])

            if not lot_id:
                continue

            lots[lot_id][type_txn].append({
                "brut":    brut,
                "comm":    comm,
                "tva":     tva,
                "libelle": libel,
            })

            lots[lot_id]["date"]     = date_val
            lots[lot_id]["date_cle"] = dcle
            lots[lot_id]["date_txn"] = date_txn
            if libel:
                lots[lot_id]["libel"] = libel

        logger.info(
            f"[PLANET CAISSE] Lots trouvés : {len(lots)} "
            f"| Ignorés : {nb_ignores}"
        )

        # ----------------------------------------------------------
        # 3. Construction des écritures comptables
        # ----------------------------------------------------------
        lignes_finales = []

        for lot_id, types in sorted(
            lots.items(), key=lambda x: x[1]["date_cle"]
        ):
            date_lot  = types["date"]
            date_txn  = types.get("date_txn", date_lot)
            libel_lot = types.get("libel", "")
            n_piece   = f"PLANET{lot_id}"

            libel_principal = _construire_libelle(
                "PLANET DU", date_txn, libel_lot, lot_id
            )

            # ---- SALES ----
            sales = types["Sale"]
            if sales:
                total_brut  = round(sum(t["brut"]       for t in sales), 2)
                total_comm  = round(sum(abs(t["comm"])  for t in sales), 2)
                total_tva   = round(sum(abs(t["tva"])   for t in sales), 2)
                total_frais = round(total_comm + total_tva, 2)
                net_sale    = round(total_brut - total_frais, 2)

                # 580005 CREDIT — brut encaissé
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_lot,
                    COL_COMPTE:     COMPTE_TRANSIT_CAISSE,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      n_piece,
                    COL_OBJET:      libel_principal,
                    COL_DEBIT:      "",
                    COL_CREDIT:     format_montant_compta(total_brut),
                    COL_JOURNAL:    JOURNAL_CEBOOBA,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })

                # COMPTE_COMM DEBIT — frais + TVA
                if total_frais != 0:
                    lignes_finales.append({
                        COL_STE:        STE_DLM,
                        COL_DATE:       date_lot,
                        COL_COMPTE:     COMPTE_COMM,
                        COL_AUX:        AUX_PLANET,
                        COL_PIECE:      n_piece,
                        COL_OBJET:      f"Frais Planet Caisse du {date_txn}",
                        COL_DEBIT:      format_montant_compta(total_frais),
                        COL_CREDIT:     "",
                        COL_JOURNAL:    JOURNAL_CEBOOBA,
                        COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                    })

                # COMPTE_PRINCIPAL DEBIT — net encaissé
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_lot,
                    COL_COMPTE:     COMPTE_PRINCIPAL,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      n_piece,
                    COL_OBJET:      f"Encaissement Planet Caisse lot {lot_id}",
                    COL_DEBIT:      format_montant_compta(net_sale),
                    COL_CREDIT:     "",
                    COL_JOURNAL:    JOURNAL_CEBOOBA,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })

            # ---- REFUNDS ----
            refunds = types["Refund"]
            if refunds:
                total_ref   = round(sum(abs(t["brut"])  for t in refunds), 2)
                total_comm  = round(sum(abs(t["comm"])  for t in refunds), 2)
                total_tva   = round(sum(abs(t["tva"])   for t in refunds), 2)
                total_frais = round(total_comm + total_tva, 2)
                net_ref     = round(total_ref - total_frais, 2)

                # 580005 DEBIT — remboursement brut
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_lot,
                    COL_COMPTE:     COMPTE_TRANSIT_CAISSE,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      n_piece,
                    COL_OBJET:      libel_principal,
                    COL_DEBIT:      format_montant_compta(total_ref),
                    COL_CREDIT:     "",
                    COL_JOURNAL:    JOURNAL_CEBOOBA,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })

                # COMPTE_COMM CREDIT — frais remboursés
                if total_frais != 0:
                    lignes_finales.append({
                        COL_STE:        STE_DLM,
                        COL_DATE:       date_lot,
                        COL_COMPTE:     COMPTE_COMM,
                        COL_AUX:        AUX_PLANET,
                        COL_PIECE:      n_piece,
                        COL_OBJET:      f"Frais remb. Planet Caisse du {date_txn}",
                        COL_DEBIT:      "",
                        COL_CREDIT:     format_montant_compta(total_frais),
                        COL_JOURNAL:    JOURNAL_CEBOOBA,
                        COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                    })

                # COMPTE_PRINCIPAL CREDIT — net remboursé
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_lot,
                    COL_COMPTE:     COMPTE_PRINCIPAL,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      n_piece,
                    COL_OBJET:      f"Remb. net Planet Caisse lot {lot_id}",
                    COL_DEBIT:      "",
                    COL_CREDIT:     format_montant_compta(net_ref),
                    COL_JOURNAL:    JOURNAL_CEBOOBA,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })

        # ----------------------------------------------------------
        # 4. Export CSV
        # ----------------------------------------------------------
        DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

        df_final = pd.DataFrame(lignes_finales, columns=COLONNES_SORTIE)
        sortie   = DOSSIER_SORTIE / f"{fichier.stem}_planet_caisse.csv"
        df_final.to_csv(sortie, sep=";", index=False, encoding="latin-1")

        logger.info(
            f"[MODULE1][PLANET CAISSE] Export réussi : {sortie.name} "
            f"({len(lignes_finales)} écritures, {len(lots)} lot(s))"
        )
        return "OK", str(sortie)

    except NotPlanetCaisseFileError as e:
        msg = str(e)
        logger.error(f"[PLANET CAISSE] {msg}")
        return "ERREUR", msg

    except Exception as e:
        msg = f"Erreur de traitement : {e}"
        logger.error(f"[PLANET CAISSE] {msg}", exc_info=True)
        return "ERREUR", msg

# ==========================================================
__all__ = ["traiter_planet_caisse", "NotPlanetCaisseFileError"]
