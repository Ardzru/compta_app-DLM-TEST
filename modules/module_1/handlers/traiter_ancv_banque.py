# modules/module_1/handlers/traiter_ancv_banque.py
"""
Handler ANCV Banque (Chèque-Vacances Connect) — Convention 899394
Fichier : RELEVE DE COMPTE CSV (séparateur ;)

Écritures générées par ligne de données :
  1. Crédit 580004  ← montant vérifié        (col K / index 11)
  2. Débit  627800  ← commission             (col N / index 13) + analytique AD-CO00-XX
  3. Débit  512120  ← montant net remboursé  (col M / index 12)

Libellé  = Format (col H / index 7) + " " + Date réception (col I / index 8)
Date     = Date valeur (col J / index 9)
Journal  = CEBOOBA
"""

import csv
from pathlib import Path
from datetime import datetime

from config import DOSSIER_SORTIE, logger
from core.utils.constantes import (
    STE_DLM,
    AUXILIAIRE_VIDE,
    ANALYTIQUE_VIDE,
    JOURNAL_CEBOOBA,
)
from core.utils.montant import to_float

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES MÉTIER
# ═══════════════════════════════════════════════════════════════════════════════

CONVENTION = "899394"

COMPTE_TRANSIT = "580004"
COMPTE_CHARGES = "627800"
COMPTE_BANQUE = "512120"
ANALYTIQUE_CHARGES = "AD-CO00-XX"

# Colonnes CSV (0-based)
COL_FORMAT = 7  # H — Format / libellé
COL_DATE_RECEP = 8  # I — Date réception (pour le libellé)
COL_DATE_VALEUR = 9  # J — Date valeur (date comptable)
COL_MONTANT_VERIFIE = 11  # K — Montant vérifié → crédit 580004
COL_MONTANT_NET = 12  # M — Montant net remboursé → débit 512120
COL_COMMISSION = 13  # N — Commission → débit 627800

LIGNE_DONNEES = 7  # Index 0-based de la 1ère ligne de données (ligne 8 Excel)

COLONNES_SORTIE = [
    "STE",
    "DATE",
    "COMPTE",
    "Auxiliaire",
    "n°pièce",
    "OBJET",
    "D",
    "C",
    "Journal",
    "Analytique",
]

# ═══════════════════════════════════════════════════════════════════════════════
# DÉTECTION
# ═══════════════════════════════════════════════════════════════════════════════


def est_fichier_ancv_banque(fichier: Path) -> bool:
    """
    Retourne True si le fichier est un relevé ANCV Connect.
    Critères :
      - Extension .csv
      - Ligne 0 contient "RELEVE DE COMPTE"
      - Ligne 3 contient le numéro de convention 899394
    """
    fichier = Path(fichier)
    if fichier.suffix.lower() != ".csv":
        return False

    try:
        with open(
            fichier, encoding="utf-8", errors="replace", newline=""
        ) as f:
            reader = csv.reader(f, delimiter=";")
            rows = []
            for i, row in enumerate(reader):
                rows.append(row)
                if i >= 4:
                    break

        # Ligne 0 : "RELEVE DE COMPTE"
        if not rows or "RELEVE DE COMPTE" not in ";".join(rows[0]).upper():
            return False

        # Ligne 3 : numéro de convention
        if len(rows) < 4:
            return False
        ligne_convention = ";".join(rows[3])
        if CONVENTION not in ligne_convention:
            return False

        logger.debug(f"[ANCV_BANQUE] Détecté : {fichier.name}")
        return True

    except Exception as e:
        logger.debug(f"est_fichier_ancv_banque({fichier.name}) : {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════


def _parser_date(valeur: str) -> str:
    """Tente plusieurs formats de date, retourne JJ/MM/AAAA ou la valeur brute."""
    valeur = valeur.strip()
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]
    for fmt in formats:
        try:
            return datetime.strptime(valeur, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    logger.warning(f"[ANCV_BANQUE] Date non parsée : '{valeur}'")
    return valeur


def _fmt(valeur: float) -> str:
    """Formate un montant en chaîne avec 2 décimales (virgule)."""
    return f"{valeur:.2f}".replace(".", ",")


# ═══════════════════════════════════════════════════════════════════════════════
# LECTURE
# ═══════════════════════════════════════════════════════════════════════════════


def _lire_lignes(fichier: Path) -> list[dict]:
    """
    Lit le CSV et retourne les lignes de données valides.
    Ignore les lignes d'en-tête (< LIGNE_DONNEES) et les lignes vides.
    Nettoie les caractères invalides UTF-8.
    """
    lignes_valides = []

    # Lecture avec nettoyage des caractères corrompus
    with open(fichier, encoding="utf-8", errors="replace", newline="") as f:
        contenu = f.read()

    # Supprimer les caractères de remplacement Unicode
    contenu = contenu.replace("\ufffd", "")

    rows = list(csv.reader(contenu.splitlines(), delimiter=";"))

    logger.debug(f"[ANCV_BANQUE] {len(rows)} lignes brutes dans {fichier.name}")

    for idx, row in enumerate(rows):
        if idx < LIGNE_DONNEES:
            continue

        if len(row) <= COL_COMMISSION:
            logger.debug(
                f"[ANCV_BANQUE] Ligne {idx + 1} ignorée (trop courte : {len(row)} cols)"
            )
            continue

        # Montant vérifié obligatoire
        montant_verifie_brut = row[COL_MONTANT_VERIFIE].strip()
        if not montant_verifie_brut:
            logger.debug(
                f"[ANCV_BANQUE] Ligne {idx + 1} ignorée (montant vérifié vide)"
            )
            continue

        montant_verifie = to_float(montant_verifie_brut)
        if montant_verifie == 0.0:
            logger.debug(
                f"[ANCV_BANQUE] Ligne {idx + 1} ignorée (montant vérifié = 0)"
            )
            continue

        montant_net = to_float(row[COL_MONTANT_NET].strip())
        commission = to_float(row[COL_COMMISSION].strip())
        format_libel = row[COL_FORMAT].strip()
        date_recep = _parser_date(row[COL_DATE_RECEP].strip())
        date_comptable = _parser_date(row[COL_DATE_VALEUR].strip())

        lignes_valides.append(
            {
                "libelle": f"{format_libel} {date_recep}",
                "date_comptable": date_comptable,
                "montant_verifie": montant_verifie,
                "montant_net": montant_net,
                "commission": commission,
            }
        )

    logger.info(
        f"[ANCV_BANQUE] {len(lignes_valides)} ligne(s) exploitable(s)"
    )
    return lignes_valides


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION DES ÉCRITURES
# ═══════════════════════════════════════════════════════════════════════════════


def _construire_ecritures(lignes: list[dict]) -> list[dict]:
    """
    Construit les 3 écritures comptables par ligne :
      1. Crédit 580004 — montant vérifié
      2. Débit  627800 — commission + analytique
      3. Débit  512120 — montant net remboursé
    """
    ecritures = []

    for ligne in lignes:
        date = ligne["date_comptable"]
        libelle = ligne["libelle"]
        m_verifie = ligne["montant_verifie"]
        m_net = ligne["montant_net"]
        commission = ligne["commission"]

        base = {
            "STE": STE_DLM,
            "DATE": date,
            "Auxiliaire": AUXILIAIRE_VIDE,
            "n°pièce": "",
            "Journal": JOURNAL_CEBOOBA,
        }

        # 1. Crédit 580004 — montant vérifié
        ecritures.append(
            {
                **base,
                "COMPTE": COMPTE_TRANSIT,
                "OBJET": libelle,
                "D": "",
                "C": _fmt(m_verifie),
                "Analytique": ANALYTIQUE_VIDE,
            }
        )

        # 2. Débit 627800 — commission (seulement si > 0)
        if commission > 0.0:
            ecritures.append(
                {
                    **base,
                    "COMPTE": COMPTE_CHARGES,
                    "OBJET": libelle,
                    "D": _fmt(commission),
                    "C": "",
                    "Analytique": ANALYTIQUE_CHARGES,
                }
            )

        # 3. Débit 512120 — montant net remboursé
        ecritures.append(
            {
                **base,
                "COMPTE": COMPTE_BANQUE,
                "OBJET": libelle,
                "D": _fmt(m_net),
                "C": "",
                "Analytique": ANALYTIQUE_VIDE,
            }
        )

    logger.info(f"[ANCV_BANQUE] {len(ecritures)} écriture(s) construite(s)")
    return ecritures


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════


def _exporter(ecritures: list[dict], fichier_source: Path) -> Path:
    """
    Écrit les écritures dans un CSV comptable.
    Utilise utf-8-sig pour compatibilité Excel Windows.
    """
    sortie = Path(DOSSIER_SORTIE) / f"ANCV_BANQUE_{fichier_source.stem}.csv"

    with open(sortie, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLONNES_SORTIE, delimiter=";")
        writer.writeheader()
        writer.writerows(ecritures)

    logger.info(
        f"[ANCV_BANQUE] Export → {sortie.name} ({len(ecritures)} écritures)"
    )
    return sortie


# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════════


def traiter_ancv_banque(fichier: Path) -> Path | None:
    """
    Point d'entrée appelé par core/dispatcher.py.

    Args:
        fichier: Chemin du fichier CSV ANCV Banque

    Returns:
        Path du fichier CSV généré, ou None si aucune donnée exploitable.
    """
    logger.info(f"[ANCV_BANQUE] ── Début traitement : {fichier.name}")

    try:
        lignes = _lire_lignes(fichier)

        if not lignes:
            logger.warning(
                f"[ANCV_BANQUE] Aucune ligne exploitable dans {fichier.name}"
            )
            return None

        ecritures = _construire_ecritures(lignes)

        if not ecritures:
            logger.warning(
                f"[ANCV_BANQUE] Aucune écriture générée pour {fichier.name}"
            )
            return None

        sortie = _exporter(ecritures, fichier)
        logger.info(f"[ANCV_BANQUE] ── Fin traitement : {sortie.name}")
        return sortie

    except Exception as e:
        logger.error(
            f"[ANCV_BANQUE] Erreur traitement {fichier.name} : {e}",
            exc_info=True,
        )
        return None
