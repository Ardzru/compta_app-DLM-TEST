import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Optional
from config import DOSSIER_SORTIE
from logger import logger
from datetime import date
from core.moniteur_schema import comparer_schema   # ← AJOUT

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotAlmaFileError(Exception):
    """Levée si le fichier ne contient aucune ligne ALMA exploitable."""
    pass

# ==========================================================
# INDEX DES COLONNES
# ==========================================================
COL_DATE      = 1   # Date de transaction   (colonne B)
COL_MONTANT   = 2   # Montant total         (colonne C)
COL_TVA       = 4   # TVA                   (colonne E)
COL_FRAIS     = 5   # Frais ALMA            (colonne F)
COL_REFERENCE = 11  # Référence transaction (colonne L)

# ==========================================================
# UTILITAIRES
# ==========================================================

def nettoyer_montant(val) -> float:
    """
    Nettoie et convertit un montant ALMA en float.
    Le format ALMA exprime les montants en centimes → division par 100.
    """
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
    """Formate une date au format JJ/MM/AAAA (libellé de pièce)."""
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        logger.warning(f"Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d/%m/%Y")

def formater_date_ecriture(val, jours_a_ajouter: int = 8) -> Optional[str]:
    """
    Calcule la date d'écriture comptable.
    Par défaut : date ALMA + 8 jours ouvrés.
    """
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        logger.warning(f"Date invalide pour calcul d'écriture : {val!r}")
        return None
    return (d + pd.Timedelta(days=jours_a_ajouter)).strftime("%d/%m/%Y")

def monter_montant(valeur: float) -> str:
    """Formate un float en chaîne comptable (virgule, 2 décimales)."""
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
    - 4 écritures par ligne : 580010DS5 / 445660 / 627800 / 512120
    - Banque (512120) : UNE seule ligne par date d'écriture
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier ALMA introuvable : {fichier}")

    logger.info(f"Traitement ALMA : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture du fichier
    # ----------------------------------------------------------
    try:
        df = pd.read_excel(fichier, engine="openpyxl")
    except Exception as e:
        logger.error(f"Impossible de lire {fichier.name} : {e}")
        raise

    # ----------------------------------------------------------
    # 1b. Vérification du schéma                    # ← AJOUT
    # ----------------------------------------------------------
    comparer_schema(df, "alma")                      # ← AJOUT

    # ----------------------------------------------------------
    # 2. Accumulation par date d'écriture
    # Structure : { date_ecriture: { "lignes": [...], "total_banque": float } }
    # ----------------------------------------------------------
    groupes: dict = defaultdict(lambda: {"lignes": [], "total_banque": 0.0})

    for idx, row in df.iterrows():

        # Dates
        date_lib      = formater_date(row.iloc[COL_DATE])
        date_ecriture = formater_date_ecriture(row.iloc[COL_DATE])

        if not date_lib or not date_ecriture:
            logger.warning(f"Ligne {idx} ignorée : date invalide")
            continue

        # Montants
        montant_achat = nettoyer_montant(row.iloc[COL_MONTANT])
        tva           = nettoyer_montant(row.iloc[COL_TVA])
        frais         = nettoyer_montant(row.iloc[COL_FRAIS])
        reference     = str(row.iloc[COL_REFERENCE]).strip()

        if montant_achat == 0 and tva == 0 and frais == 0:
            continue

        montant_net = montant_achat - (tva + frais)
        objet = f"ALMA {date.today().strftime('%d-%m-%Y')}"
        groupe      = groupes[date_ecriture]

        # Écriture 1 : Montant total vente (crédit compte transit ALMA)
        groupe["lignes"].append({
            "STE":        "DLM",
            "DATE":       date_ecriture,
            "COMPTE":     "580010DS5",
            "Auxiliaire": "",
            "n°pièce":    objet,
            "OBJET":      reference,
            "D":          "",
            "C":          monter_montant(montant_achat),
            "Journal":    "AC",
            "Analytique": "",
        })

        # Écriture 2 : TVA collectée
        groupe["lignes"].append({
            "STE":        "DLM",
            "DATE":       date_ecriture,
            "COMPTE":     "445660",
            "Auxiliaire": "",
            "n°pièce":    objet,
            "OBJET":      f"TVA {objet}",
            "D":          monter_montant(tva),
            "C":          "",
            "Journal":    "AC",
            "Analytique": "",
        })

        # Écriture 3 : Frais ALMA
        groupe["lignes"].append({
            "STE":        "DLM",
            "DATE":       date_ecriture,
            "COMPTE":     "627800",
            "Auxiliaire": "",
            "n°pièce":    objet,
            "OBJET":      f"Frais {objet}",
            "D":          monter_montant(frais),
            "C":          "",
            "Journal":    "AC",
            "Analytique": "ST-CT00-XX",
        })

        # Accumulation pour la ligne banque groupée
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

        # ✅ Même OBJET que les lignes du groupe
        objet_banque = groupe["lignes"][0]["OBJET"] if groupe["lignes"] else f"ALMA DU {date_ecriture}"

        lignes_finales.append({
            "STE": "DLM",
            "DATE": date_ecriture,
            "COMPTE": "512120",
            "Auxiliaire": "",
            "n°pièce": objet,
            "OBJET": objet,
            "D": monter_montant(total_banque),
            "C": "",
            "Journal": "AC",
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
