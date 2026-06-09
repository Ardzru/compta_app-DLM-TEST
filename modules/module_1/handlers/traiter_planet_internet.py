"""
Module 1 - Handler PLANET INTERNET
Traite les fichiers de transactions Planet Internet (Ecommerce/Payzen)
et génère les écritures comptables.

Compte transit : 580010DS5
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
    COMPTE_TRANSIT_PLANET_INTERNET,   # ← depuis constantes
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
# EXCEPTION MÉTIER
# ==========================================================

class NotPlanetInternetFileError(Exception):
    """Levée si le fichier Planet Internet n'est pas exploitable."""
    pass

# ==========================================================
# COLONNES ATTENDUES (indices 0-based) — identiques à Caisse
# ==========================================================
_COL_TYPE     = PLANET_COL["type"]      # 6
_COL_LOT      = PLANET_COL["lot"]       # 11
_COL_BRUT     = PLANET_COL["brut"]      # 13
_COL_DATE_TXN = PLANET_COL["date_txn"]  # 15
_COL_DATE_VAL = PLANET_COL["date_val_internet"]  # 29
_COL_COMM     = PLANET_COL["comm"]      # 23
_COL_LIBEL    = PLANET_COL["libel"]     # 31
_COL_TVA      = PLANET_COL["tva"]       # 39

# ==========================================================
# UTILITAIRES INTERNES — identiques à Caisse
# ==========================================================

def _formater_date(val) -> str:
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
    try:
        return float(val) if val not in (None, "", "NA") else 0.0
    except (ValueError, TypeError):
        return 0.0

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_planet_internet(fichier: Path) -> tuple[str, str]:
    """
    Traite un fichier de transactions Planet Internet (Ecommerce/Payzen).

    Retourne:
        ("OK", chemin_fichier) | ("ERREUR", message)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        msg = f"Fichier Planet Internet introuvable : {fichier}"
        logger.error(f"[PLANET INTERNET] {msg}")
        return "ERREUR", msg

    logger.info(f"[MODULE1][PLANET INTERNET] Début traitement : {fichier.name}")

    try:
        # ----------------------------------------------------------
        # 1. Lecture Excel
        # ----------------------------------------------------------
        try:
            wb = openpyxl.load_workbook(fichier, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
        except Exception as e:
            msg = f"Impossible de lire {fichier.name} : {e}"
            logger.error(f"[PLANET INTERNET] {msg}")
            raise NotPlanetInternetFileError(msg)

        if len(rows) < 2:
            msg = "Fichier vide ou sans données"
            logger.warning(f"[PLANET INTERNET] {msg}")
            raise NotPlanetInternetFileError(msg)

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

            lot_id   = str(row[_COL_LOT]).strip()   if row[_COL_LOT]   else ""
            brut     = _to_float(row[_COL_BRUT])
            comm     = _to_float(row[_COL_COMM])
            tva      = _to_float(row[_COL_TVA])
            libel    = str(row[_COL_LIBEL]).strip() if row[_COL_LIBEL] else ""
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
            f"[PLANET INTERNET] Lots trouvés : {len(lots)} | Ignorés : {nb_ignores}"
        )

        # ----------------------------------------------------------
        # 3. Construction des écritures comptables
        # ----------------------------------------------------------
        lignes_finales = []

        for lot_id, types in sorted(
            lots.items(), key=lambda x: x[1]["date_cle"]
        ):
            date_lot = types["date"]
            date_txn = types.get("date_txn", date_lot)
            n_piece  = f"PLANET{lot_id}"
            libel_principal = f"PLANET INTERNET DU {date_txn}"

            # ---- SALES ----
            sales = types["Sale"]
            if sales:
                total_brut  = round(sum(t["brut"]      for t in sales), 2)
                total_comm  = round(sum(abs(t["comm"]) for t in sales), 2)
                total_tva   = round(sum(abs(t["tva"])  for t in sales), 2)
                total_frais = round(total_comm + total_tva, 2)
                net_sale    = round(total_brut - total_frais, 2)

                # 580010DS5 CREDIT
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_lot,
                    COL_COMPTE:     COMPTE_TRANSIT_PLANET_INTERNET,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      n_piece,
                    COL_OBJET:      libel_principal,
                    COL_DEBIT:      "",
                    COL_CREDIT:     format_montant_compta(total_brut),
                    COL_JOURNAL:    JOURNAL_CEBOOBA,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })

                # COMPTE_COMM DEBIT
                if total_frais != 0:
                    lignes_finales.append({
                        COL_STE:        STE_DLM,
                        COL_DATE:       date_lot,
                        COL_COMPTE:     COMPTE_COMM,
                        COL_AUX:        AUX_PLANET,
                        COL_PIECE:      n_piece,
                        COL_OBJET:      f"Frais Planet Internet du {date_txn}",
                        COL_DEBIT:      format_montant_compta(total_frais),
                        COL_CREDIT:     "",
                        COL_JOURNAL:    JOURNAL_CEBOOBA,
                        COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                    })

                # COMPTE_PRINCIPAL DEBIT
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_lot,
                    COL_COMPTE:     COMPTE_PRINCIPAL,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      n_piece,
                    COL_OBJET:      f"Encaissement Planet Internet lot {lot_id}",
                    COL_DEBIT:      format_montant_compta(net_sale),
                    COL_CREDIT:     "",
                    COL_JOURNAL:    JOURNAL_CEBOOBA,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })

            # ---- REFUNDS ----
            refunds = types["Refund"]
            if refunds:
                total_ref   = round(sum(abs(t["brut"]) for t in refunds), 2)
                total_comm  = round(sum(abs(t["comm"]) for t in refunds), 2)
                total_tva   = round(sum(abs(t["tva"])  for t in refunds), 2)
                total_frais = round(total_comm + total_tva, 2)
                net_ref     = round(total_ref - total_frais, 2)

                # 580010DS5 DEBIT
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_lot,
                    COL_COMPTE:     COMPTE_TRANSIT_PLANET_INTERNET,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      n_piece,
                    COL_OBJET:      libel_principal,
                    COL_DEBIT:      format_montant_compta(total_ref),
                    COL_CREDIT:     "",
                    COL_JOURNAL:    JOURNAL_CEBOOBA,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })

                # COMPTE_COMM CREDIT
                if total_frais != 0:
                    lignes_finales.append({
                        COL_STE:        STE_DLM,
                        COL_DATE:       date_lot,
                        COL_COMPTE:     COMPTE_COMM,
                        COL_AUX:        AUX_PLANET,
                        COL_PIECE:      n_piece,
                        COL_OBJET:      f"Frais remb. Planet Internet du {date_txn}",
                        COL_DEBIT:      "",
                        COL_CREDIT:     format_montant_compta(total_frais),
                        COL_JOURNAL:    JOURNAL_CEBOOBA,
                        COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                    })

                # COMPTE_PRINCIPAL CREDIT
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_lot,
                    COL_COMPTE:     COMPTE_PRINCIPAL,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      n_piece,
                    COL_OBJET:      f"Remb. net Planet Internet lot {lot_id}",
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
        sortie   = DOSSIER_SORTIE / f"{fichier.stem}_planet_internet.csv"
        df_final.to_csv(sortie, sep=";", index=False, encoding="latin-1")

        logger.info(
            f"[MODULE1][PLANET INTERNET] Export réussi : {sortie.name} "
            f"({len(lignes_finales)} écritures, {len(lots)} lot(s))"
        )
        return "OK", str(sortie)

    except NotPlanetInternetFileError as e:
        msg = str(e)
        logger.error(f"[PLANET INTERNET] {msg}")
        return "ERREUR", msg

    except Exception as e:
        msg = f"Erreur de traitement : {e}"
        logger.error(f"[PLANET INTERNET] {msg}", exc_info=True)
        return "ERREUR", msg

# ==========================================================
__all__ = ["traiter_planet_internet", "NotPlanetInternetFileError"]
