import csv
import openpyxl
from pathlib import Path
from typing import Optional
from collections import defaultdict
from config import DOSSIER_SORTIE
from logger import logger

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================
class NotPlanetFileError(Exception):
    pass

# ==========================================================
# CONSTANTES COMPTABLES
# ==========================================================
STE        = "DLM"
JOURNAL    = "CEBOOBA"
ANALYTIQUE = ""

COMPTE_PRINCIPAL = "512120"
COMPTE_VENTE     = "580010DS5"
COMPTE_COMM      = "401000"
COMPTE_TVA       = "401000"
AUX_PLANET       = "PLANET MERCHANT SERVICES"

# ==========================================================
# MAPPING COLONNES (0-based)
# ==========================================================
COL_TYPE     = 6
COL_LOT      = 11
COL_BRUT     = 13
COL_DATE_TXN = 15   # Date de transaction (pour libellé)
COL_DATE_VAL = 30   # Colonne AE = date de valeur (date comptable)
COL_COMM     = 23
COL_LIBEL    = 31
COL_TVA      = 39

# ==========================================================
# COLONNES SORTIE
# ==========================================================
COLONNES_SORTIE = [
    "STE", "DATE", "COMPTE", "Auxiliaire",
    "n°pièce", "Libellé", "DEBIT", "CREDIT",
    "JOURNAL", "ANALYTIQUE",
]

# ==========================================================
# UTILITAIRES
# ==========================================================
def _format_date(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if "-" in s:
        s = s[:10]
        y, m, d = s.split("-")
        return f"{d}/{m}/{y}"
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

def _format_montant(val) -> str:
    try:
        return f"{abs(round(float(val), 2)):.2f}".replace(".", ",")
    except (ValueError, TypeError):
        return "0,00"

def _float(val) -> float:
    try:
        return float(val) if val not in (None, "", "NA") else 0.0
    except (ValueError, TypeError):
        return 0.0

def _row(ste, date, compte, auxiliaire, piece, libelle, debit, credit):
    return [ste, date, compte, auxiliaire, piece, libelle,
            debit, credit, JOURNAL, ANALYTIQUE]

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================
def traiter_planet(fichier: Path) -> Optional[Path]:
    logger.info(f"Traitement Planet : {fichier.name}")

    # ----------------------------------------------------------
    # ÉTAPE 1 — Lecture Excel
    # ----------------------------------------------------------
    try:
        wb = openpyxl.load_workbook(fichier, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
    except Exception as e:
        raise NotPlanetFileError(f"Impossible de lire {fichier.name} : {e}")

    if len(rows) < 2:
        raise NotPlanetFileError("Fichier vide ou sans données.")

    # ----------------------------------------------------------
    # ÉTAPE 2 — Lecture et regroupement par lot
    # ----------------------------------------------------------
    lots       = defaultdict(lambda: {"Sale": [], "Refund": [], "date": "", "date_cle": "", "date_txn": ""})
    nb_ignores = 0

    max_col = max(COL_TYPE, COL_LOT, COL_BRUT, COL_DATE_TXN, COL_DATE_VAL, COL_COMM, COL_LIBEL, COL_TVA)

    for i, row in enumerate(rows[1:], start=2):
        if len(row) <= max_col:
            continue

        type_txn = str(row[COL_TYPE]).strip() if row[COL_TYPE] else ""

        if type_txn == "Declined Trx":
            nb_ignores += 1
            continue

        if type_txn not in ("Sale", "Refund"):
            continue

        lot_id   = str(row[COL_LOT]).strip() if row[COL_LOT] else ""
        brut     = _float(row[COL_BRUT])
        comm     = _float(row[COL_COMM])
        tva      = _float(row[COL_TVA])
        libel    = str(row[COL_LIBEL]).strip() if row[COL_LIBEL] else ""
        date_txn = _format_date(row[COL_DATE_TXN])   # date transaction → libellé
        date_val = _format_date(row[COL_DATE_VAL])    # date valeur (AE) → date comptable
        dcle     = _date_cle(row[COL_DATE_VAL])

        if not lot_id:
            continue

        lots[lot_id][type_txn].append({
            "brut":     brut,
            "comm":     comm,
            "tva":      tva,
            "libelle":  libel,
        })

        # On garde la dernière date rencontrée pour le lot
        lots[lot_id]["date"]     = date_val
        lots[lot_id]["date_cle"] = dcle
        lots[lot_id]["date_txn"] = date_txn

    logger.info(f"Lots trouvés : {len(lots)} | Ignorés : {nb_ignores}")

    # ----------------------------------------------------------
    # ÉTAPE 3 — Construction des écritures comptables
    # ----------------------------------------------------------
    lignes_sortie = []

    for lot_id, types in sorted(lots.items(), key=lambda x: x[1]["date_cle"]):

        date_lot = types["date"]
        date_txn = types.get("date_txn", date_lot)
        n_piece  = f"PLANET{lot_id}"

        # ---- SALES ----
        sales = types["Sale"]
        if sales:
            total_brut  = round(sum(t["brut"]     for t in sales), 2)
            total_comm  = round(sum(abs(t["comm"]) for t in sales), 2)
            total_tva   = round(sum(abs(t["tva"])  for t in sales), 2)
            total_frais = round(total_comm + total_tva, 2)
            net_sale    = round(total_brut - total_frais, 2)

            # 580010DS5 CREDIT — libellé avec date transaction
            lignes_sortie.append(_row(
                STE, date_lot, COMPTE_VENTE, "",
                n_piece, f"PLANET DU {date_txn}",
                "", _format_montant(total_brut),
            ))

            # 401000 DEBIT — frais + TVA regroupés sur 1 ligne
            if total_frais != 0:
                lignes_sortie.append(_row(
                    STE, date_lot, COMPTE_COMM, AUX_PLANET,
                    n_piece, f"Frais Planet du {date_txn}",
                    _format_montant(total_frais), "",
                ))

            # 512120 DEBIT — net encaissé
            lignes_sortie.append(_row(
                STE, date_lot, COMPTE_PRINCIPAL, "",
                n_piece, f"Encaissement Planet lot {lot_id}",
                _format_montant(net_sale), "",
            ))

        # ---- REFUNDS ----
        refunds = types["Refund"]
        if refunds:
            total_ref   = round(sum(abs(t["brut"]) for t in refunds), 2)
            total_comm  = round(sum(abs(t["comm"]) for t in refunds), 2)
            total_tva   = round(sum(abs(t["tva"])  for t in refunds), 2)
            total_frais = round(total_comm + total_tva, 2)
            net_ref     = round(total_ref - total_frais, 2)

            # 580010DS5 DEBIT
            lignes_sortie.append(_row(
                STE, date_lot, COMPTE_VENTE, "",
                n_piece, f"PLANET DU {date_txn}",
                _format_montant(total_ref), "",
            ))

            # 401000 CREDIT — frais regroupés
            if total_frais != 0:
                lignes_sortie.append(_row(
                    STE, date_lot, COMPTE_COMM, AUX_PLANET,
                    n_piece, f"Frais remb. Planet du {date_txn}",
                    "", _format_montant(total_frais),
                ))

            # 512120 CREDIT — net remboursé
            lignes_sortie.append(_row(
                STE, date_lot, COMPTE_PRINCIPAL, "",
                n_piece, f"Remb. net Planet lot {lot_id}",
                "", _format_montant(net_ref),
            ))

    # ----------------------------------------------------------
    # ÉTAPE 4 — Export CSV
    # ----------------------------------------------------------
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_planet.csv"

    with open(sortie, "w", newline="", encoding="latin1") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(COLONNES_SORTIE)
        for ligne in lignes_sortie:
            writer.writerow(ligne)

    logger.info(
        f"Export PLANET : {sortie.name} "
        f"({len(lignes_sortie)} écritures, "
        f"{len(lots)} lot(s))"
    )
    return sortie
