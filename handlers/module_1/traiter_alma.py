import csv
import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Optional
from config import DOSSIER_SORTIE
from logger import logger
from datetime import date
from core.moniteur_schema import comparer_schema

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotAlmaFileError(Exception):
    """Levée si le fichier ne contient aucune ligne ALMA exploitable."""
    pass

# ==========================================================
# INDEX DES COLONNES
# ==========================================================
COL_DATE      = 1
COL_MONTANT   = 2
COL_TVA       = 4
COL_FRAIS     = 5
COL_REFERENCE = 11

# ==========================================================
# CONSTANTES COMPTABLES
# ==========================================================
STE              = "DLM"
JOURNAL          = "AC"
COMPTE_TRANSIT   = "580010DS5"
COMPTE_BANQUE    = "512120"
COMPTE_FOURN     = "401000"
AUXILIAIRE_FOURN = "ALMA"

# ==========================================================
# UTILITAIRES
# ==========================================================

def nettoyer_montant(val) -> float:
    if pd.isna(val):
        return 0.0
    s = str(val).strip()
    s = s.replace(".", "").replace("-", "").replace(",", ".")
    try:
        return float(s) / 100
    except ValueError:
        logger.warning(f"Montant invalide ignoré : {val!r}")
        return 0.0

def formater_date(val) -> Optional[str]:
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        logger.warning(f"Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d/%m/%Y")

def formater_date_ecriture(val, jours_a_ajouter: int = 8) -> Optional[str]:
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        logger.warning(f"Date invalide pour calcul d'écriture : {val!r}")
        return None
    return (d + pd.Timedelta(days=jours_a_ajouter)).strftime("%d/%m/%Y")

def monter_montant(valeur: float) -> str:
    return f"{abs(valeur):.2f}".replace(".", ",")

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_alma(fichier: Path) -> None:
    """
    Traite un fichier ALMA et génère les écritures comptables.

    Règles métier :
    - Montants en centimes → divisés par 100
    - Date d'écriture = date transaction + 8 jours
    - Écritures par ligne :
        580010DS5   → C  (montant total vente, compte transit)
        401000/ALMA → D  (frais TTC = TVA + frais HT, compte fournisseur)
        512120      → D  (montant net, UNE ligne par date d'écriture)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier ALMA introuvable : {fichier}")

    logger.info(f"Traitement ALMA : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture
    # ----------------------------------------------------------
    try:
        df = pd.read_excel(fichier, engine="openpyxl")
    except Exception as e:
        logger.error(f"Impossible de lire {fichier.name} : {e}")
        raise

    # ----------------------------------------------------------
    # 1b. Vérification du schéma
    # ----------------------------------------------------------
    comparer_schema(df, "alma")

    # ----------------------------------------------------------
    # 2. Accumulation par date d'écriture
    # ----------------------------------------------------------
    groupes: dict = defaultdict(lambda: {"lignes": [], "total_banque": 0.0})

    for idx, row in df.iterrows():

        date_lib      = formater_date(row.iloc[COL_DATE])
        date_ecriture = formater_date_ecriture(row.iloc[COL_DATE])

        if not date_lib or not date_ecriture:
            logger.warning(f"Ligne {idx} ignorée : date invalide")
            continue

        montant_achat = nettoyer_montant(row.iloc[COL_MONTANT])
        tva           = nettoyer_montant(row.iloc[COL_TVA])
        frais         = nettoyer_montant(row.iloc[COL_FRAIS])
        reference     = str(row.iloc[COL_REFERENCE]).strip()

        if montant_achat == 0 and tva == 0 and frais == 0:
            continue

        frais_ttc   = round(tva + frais, 2)
        montant_net = round(montant_achat - frais_ttc, 2)
        objet       = f"ALMA {date.today().strftime('%d-%m-%Y')}"
        groupe      = groupes[date_ecriture]

        # ── Écriture 1 : Compte transit (crédit montant total) ──
        groupe["lignes"].append({
            "STE":        STE,
            "DATE":       date_ecriture,
            "COMPTE":     COMPTE_TRANSIT,
            "Auxiliaire": "",
            "n°pièce":    objet,
            "OBJET":      reference,
            "D":          "",
            "C":          monter_montant(montant_achat),
            "Journal":    JOURNAL,
            "Analytique": "",
        })

        # ── Écriture 2 : Fournisseur ALMA (débit frais TTC) ──
        groupe["lignes"].append({
            "STE":        STE,
            "DATE":       date_ecriture,
            "COMPTE":     COMPTE_FOURN,
            "Auxiliaire": AUXILIAIRE_FOURN,
            "n°pièce":    objet,
            "OBJET":      f"Frais {objet}",
            "D":          monter_montant(frais_ttc),
            "C":          "",
            "Journal":    JOURNAL,
            "Analytique": "",
        })

        logger.debug(
            f"Ligne {idx} | achat={montant_achat} "
            f"tva={tva} frais={frais} "
            f"frais_ttc={frais_ttc} net={montant_net}"
        )

        # Accumulation banque
        groupe["total_banque"] += montant_net

    # ----------------------------------------------------------
    # 3. Génération finale : une ligne banque par date d'écriture
    # ----------------------------------------------------------
    if not groupes:
        raise NotAlmaFileError(f"Aucune ligne ALMA exploitable dans {fichier.name}")

    lignes_finales = []

    for date_ecriture, groupe in sorted(groupes.items()):

        lignes_finales.extend(groupe["lignes"])

        total_banque = round(groupe["total_banque"], 2)

        if total_banque == 0.0:
            logger.warning(f"Total banque nul pour {date_ecriture}, ligne banque ignorée")
            continue

        objet_banque = f"ALMA {date.today().strftime('%d-%m-%Y')}"

        # ── Écriture 3 : Banque (débit, groupée par date) ──
        lignes_finales.append({
            "STE":        STE,
            "DATE":       date_ecriture,
            "COMPTE":     COMPTE_BANQUE,
            "Auxiliaire": "",
            "n°pièce":    objet_banque,
            "OBJET":      objet_banque,
            "D":          monter_montant(total_banque),
            "C":          "",
            "Journal":    JOURNAL,
            "Analytique": "",
        })

    # ----------------------------------------------------------
    # 4. Export CSV
    # ----------------------------------------------------------
    if not lignes_finales:
        raise NotAlmaFileError(f"Aucune écriture générée pour {fichier.name}")

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    df_final = pd.DataFrame(lignes_finales)
    sortie   = DOSSIER_SORTIE / f"{fichier.stem}_alma.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export ALMA : {sortie.name} ({len(lignes_finales)} écritures)")
