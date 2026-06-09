"""
Module 1 - Handler ALMA
Logique métier identique à l'original, adaptée au nouveau core.
"""

from pathlib import Path
from collections import defaultdict
from typing import Optional
from datetime import date as date_module
import pandas as pd

from config import DOSSIER_SORTIE
from config import logger
from core.moniteur_schema import comparer_schema
from core.utils.montant import format_montant_compta
from core.utils.constantes import (
    STE_DLM,
    COMPTE_TRANSIT_ALMA,
    COMPTE_BANQUE_ALMA,
    COMPTE_FOURN_ALMA,
    JOURNAL_AC,
    AUXILIAIRE_ALMA,
    ANALYTIQUE_VIDE,
    COL_STE, COL_DATE, COL_COMPTE, COL_AUX,
    COL_PIECE, COL_OBJET, COL_DEBIT, COL_CREDIT,
    COL_JOURNAL, COL_ANALYTIQUE,
    COLONNES_SORTIE,
)

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotAlmaFileError(Exception):
    """Levée si le fichier ne contient aucune ligne ALMA exploitable."""
    pass

# ==========================================================
# INDEX DES COLONNES (positions fixes)
# ==========================================================
_COL_DATE      = 1
_COL_MONTANT   = 2
_COL_TVA       = 4
_COL_FRAIS     = 5
_COL_REFERENCE = 11

# ==========================================================
# UTILITAIRES INTERNES
# ==========================================================

def _nettoyer_montant(val) -> float:
    """Montants ALMA en centimes → divise par 100"""
    if pd.isna(val):
        return 0.0
    s = str(val).strip()
    s = s.replace(".", "").replace("-", "").replace(",", ".")
    try:
        return float(s) / 100
    except ValueError:
        logger.warning(f"[ALMA] Montant invalide ignoré : {val!r}")
        return 0.0


def _formater_date(val) -> Optional[str]:
    """JJ/MM/YYYY"""
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        logger.warning(f"[ALMA] Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d/%m/%Y")


def _formater_date_ecriture(val, jours_a_ajouter: int = 8) -> Optional[str]:
    """JJ/MM/YYYY avec décalage (défaut +8 jours)"""
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        logger.warning(f"[ALMA] Date invalide pour calcul d'écriture : {val!r}")
        return None
    return (d + pd.Timedelta(days=jours_a_ajouter)).strftime("%d/%m/%Y")


def _generer_objet() -> str:
    """Libellé standard : 'ALMA JJ-MM-YYYY'"""
    return f"ALMA {date_module.today().strftime('%d-%m-%Y')}"


# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_alma(fichier: Path) -> tuple[str, str]:
    """
    Traite un fichier ALMA et génère les écritures comptables.

    Règles métier :
    - Montants en centimes → divisés par 100
    - Date d'écriture = date transaction + 8 jours
    - Écritures par ligne :
        580010DS5   → C  (montant total vente, compte transit)
        401000/ALMA → D  (frais TTC = TVA + frais HT, compte fournisseur)
        512120      → D  (montant net, UNE ligne par date d'écriture)

    Returns:
        ("OK", chemin_sortie) | ("ERREUR", message) | ("PARTIEL", "")
    """

    fichier = Path(fichier)
    if not fichier.exists():
        logger.error(f"[ALMA] Fichier introuvable : {fichier}")
        return "ERREUR", f"Fichier introuvable : {fichier}"

    logger.info(f"[MODULE1][ALMA] Début traitement : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture
    # ----------------------------------------------------------
    try:
        df = pd.read_excel(fichier, engine="openpyxl")
    except Exception as e:
        logger.error(f"[ALMA] Impossible de lire {fichier.name} : {e}")
        return "ERREUR", f"Impossible de lire le fichier : {e}"

    # ----------------------------------------------------------
    # 2. Vérification du schéma
    # ----------------------------------------------------------
    try:
        comparer_schema(df, "alma")
    except Exception as e:
        logger.warning(f"[ALMA] Schéma invalide : {e}")
        # Continuer malgré tout (peut être compatible)

    # ----------------------------------------------------------
    # 3. Accumulation par date d'écriture
    # ----------------------------------------------------------
    groupes: dict = defaultdict(lambda: {"lignes": [], "total_banque": 0.0})

    for idx, row in df.iterrows():

        date_lib      = _formater_date(row.iloc[_COL_DATE])
        date_ecriture = _formater_date_ecriture(row.iloc[_COL_DATE])

        if not date_lib or not date_ecriture:
            logger.warning(f"[ALMA] Ligne {idx} ignorée : date invalide")
            continue

        montant_achat = _nettoyer_montant(row.iloc[_COL_MONTANT])
        tva           = _nettoyer_montant(row.iloc[_COL_TVA])
        frais         = _nettoyer_montant(row.iloc[_COL_FRAIS])
        reference     = str(row.iloc[_COL_REFERENCE]).strip() if _COL_REFERENCE < len(row) else ""

        if montant_achat == 0 and tva == 0 and frais == 0:
            continue

        frais_ttc   = round(tva + frais, 2)
        montant_net = round(montant_achat - frais_ttc, 2)
        objet       = _generer_objet()
        groupe      = groupes[date_ecriture]

        # ── Écriture 1 : Compte transit (crédit montant total) ──
        groupe["lignes"].append({
            COL_STE:        STE_DLM,
            COL_DATE:       date_ecriture,
            COL_COMPTE:     COMPTE_TRANSIT_ALMA,
            COL_AUX:        "",
            COL_PIECE:      objet,
            COL_OBJET:      reference,
            COL_DEBIT:      "",
            COL_CREDIT:     format_montant_compta(montant_achat),
            COL_JOURNAL:    JOURNAL_AC,
            COL_ANALYTIQUE: ANALYTIQUE_VIDE,
        })

        # ── Écriture 2 : Fournisseur ALMA (débit frais TTC) ──
        groupe["lignes"].append({
            COL_STE:        STE_DLM,
            COL_DATE:       date_ecriture,
            COL_COMPTE:     COMPTE_FOURN_ALMA,
            COL_AUX:        AUXILIAIRE_ALMA,
            COL_PIECE:      objet,
            COL_OBJET:      f"Frais {objet}",
            COL_DEBIT:      format_montant_compta(frais_ttc),
            COL_CREDIT:     "",
            COL_JOURNAL:    JOURNAL_AC,
            COL_ANALYTIQUE: ANALYTIQUE_VIDE,
        })

        logger.debug(
            f"[ALMA] Ligne {idx} | achat={montant_achat} "
            f"tva={tva} frais={frais} "
            f"frais_ttc={frais_ttc} net={montant_net}"
        )

        # Accumulation banque
        groupe["total_banque"] += montant_net

    # ----------------------------------------------------------
    # 4. Génération finale : une ligne banque par date d'écriture
    # ----------------------------------------------------------
    if not groupes:
        msg = f"Aucune ligne ALMA exploitable dans {fichier.name}"
        logger.warning(f"[ALMA] {msg}")
        return "ERREUR", msg

    lignes_finales = []

    for date_ecriture, groupe in sorted(groupes.items()):

        lignes_finales.extend(groupe["lignes"])

        total_banque = round(groupe["total_banque"], 2)

        if total_banque == 0.0:
            logger.warning(f"[ALMA] Total banque nul pour {date_ecriture}, ligne banque ignorée")
            continue

        objet_banque = _generer_objet()

        # ── Écriture 3 : Banque (débit, groupée par date) ──
        lignes_finales.append({
            COL_STE:        STE_DLM,
            COL_DATE:       date_ecriture,
            COL_COMPTE:     COMPTE_BANQUE_ALMA,
            COL_AUX:        "",
            COL_PIECE:      objet_banque,
            COL_OBJET:      objet_banque,
            COL_DEBIT:      format_montant_compta(total_banque),
            COL_CREDIT:     "",
            COL_JOURNAL:    JOURNAL_AC,
            COL_ANALYTIQUE: ANALYTIQUE_VIDE,
        })

    # ----------------------------------------------------------
    # 5. Export CSV
    # ----------------------------------------------------------
    if not lignes_finales:
        msg = f"Aucune écriture générée pour {fichier.name}"
        logger.error(f"[ALMA] {msg}")
        return "ERREUR", msg

    try:
        DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

        df_final = pd.DataFrame(lignes_finales, columns=COLONNES_SORTIE)
        sortie   = DOSSIER_SORTIE / f"{fichier.stem}_alma.csv"
        df_final.to_csv(sortie, sep=";", index=False, encoding="latin-1")

        logger.info(
            f"[MODULE1][ALMA] Export réussi : {sortie.name} ({len(lignes_finales)} écritures)"
        )
        return "OK", str(sortie)

    except Exception as e:
        logger.error(f"[ALMA] Erreur à l'export : {e}")
        return "ERREUR", f"Erreur à l'export : {e}"


# ==========================================================
__all__ = ["traiter_alma"]
