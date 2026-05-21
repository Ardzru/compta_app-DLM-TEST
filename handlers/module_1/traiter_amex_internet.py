import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Optional
from config import DOSSIER_SORTIE
from logger import logger
from core.moniteur_schema import comparer_schema          # ← AJOUT

# ==========================================================
# INDEX DES COLONNES
# ==========================================================
COL_DATE_LIB    = 0   # Date affichée (libellé)
COL_DATE_COMPTA = 13  # Date comptable
COL_D           = 3   # Montant brut
COL_E           = 4   # Montant crédité / débité
COL_G           = 6   # Frais AMEX
COL_I           = 8   # Montant net
COL_SIGNATURE   = 14  # Signature (SITE / CAISSE)

# ==========================================================
# UTILITAIRES
# ==========================================================

def nettoyer_montant(val) -> float:
    """Nettoie et convertit un montant AMEX en float."""
    if pd.isna(val):
        return 0.0

    s = str(val).strip()
    s = s.replace(" ", "").replace(".", "").replace(",", ".")

    if s.endswith("-"):
        s = "-" + s[:-1]

    try:
        return float(s)
    except ValueError:
        logger.warning(f"Montant invalide ignoré : {val!r}")
        return 0.0

def formater_date(val) -> Optional[str]:
    """Formate une date au format JJ/MM/AAAA."""
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        logger.warning(f"Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d/%m/%Y")

def monter_montant(valeur: float) -> str:
    """Formate un float en chaîne comptable (virgule, 2 décimales)."""
    return f"{abs(valeur):.2f}".replace(".", ",")

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_amex_internet(fichier: Path) -> None:
    """
    Traite un fichier AMEX Internet et génère les écritures comptables.

    Règles métier :
    - Seules les lignes contenant 'SITE' en colonne 14 sont traitées
    - CAS 1 : Remboursement client  (E < 0, G == 0)
    - CAS 2 : Encaissement simple   (E > 0)
    - CAS 3 : Encaissement avec frais
    - Banque (512120) : UNE seule ligne par date comptable
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier AMEX Internet introuvable : {fichier}")

    logger.info(f"Traitement AMEX INTERNET : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture du fichier
    # ----------------------------------------------------------
    try:
        engine = "xlrd" if fichier.suffix.lower() == ".xls" else "openpyxl"
        df = pd.read_excel(fichier, header=None, engine=engine)
    except Exception as e:
        logger.error(f"Impossible de lire {fichier.name} : {e}")
        raise

    # ----------------------------------------------------------
    # 1b. Vérification du schéma                               # ← AJOUT
    # ----------------------------------------------------------
    comparer_schema(df, "amex_internet")                       # ← AJOUT

    # ----------------------------------------------------------
    # 2. Accumulation par date comptable
    # Structure : { date_compta: { "lignes": [...], "total_banque": float } }
    # ----------------------------------------------------------
    groupes: dict = defaultdict(lambda: {"lignes": [], "total_banque": 0.0})

    for idx, row in df.iterrows():

        # Filtre AMEX Internet uniquement
        signature = str(row[COL_SIGNATURE]).strip().upper()
        if "SITE" not in signature:
            continue

        # Dates
        date_lib    = formater_date(row[COL_DATE_LIB])
        date_compta = formater_date(row[COL_DATE_COMPTA])
        if not date_lib or not date_compta:
            logger.warning(f"Ligne {idx} ignorée : date invalide")
            continue

        # Montants
        D = nettoyer_montant(row[COL_D])
        E = nettoyer_montant(row[COL_E])
        G = nettoyer_montant(row[COL_G])
        I = nettoyer_montant(row[COL_I])

        if D == 0 and E == 0 and G == 0 and I == 0:
            continue

        piece  = f"AMEX INTERNET"
        groupe = groupes[date_compta]

        # ----------------------------------------------------------
        # CAS 1 — REMBOURSEMENT CLIENT (E < 0, pas de frais)
        # ----------------------------------------------------------
        if E < 0 and G == 0:
            montant = abs(E)

            groupe["lignes"].append({
                "STE":        "DLM",
                "DATE":       date_compta,
                "COMPTE":     "580010DS5",
                "Auxiliaire": "",
                "n°pièce":    piece,
                "OBJET":      f"AMEX INTERNET DU {date_lib}",
                "D":          monter_montant(montant),
                "C":          "",
                "Journal":    "CEBOOBA",
                "Analytique": "",
            })

            groupe["total_banque"] -= montant

        # ----------------------------------------------------------
        # CAS 2 — ENCAISSEMENT SIMPLE (E > 0, sans frais)
        # ----------------------------------------------------------
        elif E > 0 and G == 0:

            groupe["lignes"].append({
                "STE":        "DLM",
                "DATE":       date_compta,
                "COMPTE":     "580010DS5",
                "Auxiliaire": "",
                "n°pièce":    piece,
                "OBJET":      f"AMEX INTERNET DU {date_lib}",
                "D":          "",
                "C":          monter_montant(E),
                "Journal":    "CEBOOBA",
                "Analytique": "",
            })

            groupe["total_banque"] += I

        # ----------------------------------------------------------
        # CAS 3 — ENCAISSEMENT AVEC FRAIS AMEX
        # ----------------------------------------------------------
        else:

            groupe["lignes"].append({
                "STE":        "DLM",
                "DATE":       date_compta,
                "COMPTE":     "580010DS5",
                "Auxiliaire": "",
                "n°pièce":    piece,
                "OBJET":      f"AMEX INTERNET DU {date_lib}",
                "D":          "",
                "C":          monter_montant(D),
                "Journal":    "CEBOOBA",
                "Analytique": "",
            })

            groupe["lignes"].append({
                "STE":        "DLM",
                "DATE":       date_compta,
                "COMPTE":     "627800",
                "Auxiliaire": "",
                "n°pièce":    piece,
                "OBJET":      f"FRAIS AMEX - {piece}",
                "D":          monter_montant(G),
                "C":          "",
                "Journal":    "CEBOOBA",
                "Analytique": "ST-CT00-XX",
            })

            groupe["total_banque"] += I

    # ----------------------------------------------------------
    # 3. Génération finale : une ligne banque par date comptable
    # ----------------------------------------------------------
    lignes_finales = []

    for date_compta, groupe in sorted(groupes.items()):

        lignes_finales.extend(groupe["lignes"])

        total_banque = round(groupe["total_banque"], 2)

        if total_banque == 0.0:
            logger.warning(f"Total banque nul pour {date_compta}, ligne banque ignorée")
            continue

        # ✅ Même OBJET que les lignes du groupe
        objet_banque = groupe["lignes"][0]["OBJET"] if groupe["lignes"] else f"AMEX INTERNET DU {date_compta}"

        lignes_finales.append({
            "STE": "DLM",
            "DATE": date_compta,
            "COMPTE": "512120",
            "Auxiliaire": "",
            "n°pièce": piece,
            "OBJET": objet_banque,
            "D": monter_montant(total_banque),
            "C": "",
            "Journal": "CEBOOBA",
            "Analytique": "",
        })

    # ----------------------------------------------------------
    # 4. Export CSV
    # ----------------------------------------------------------
    if not lignes_finales:
        logger.warning(f"Aucune écriture générée pour {fichier.name}")
        return

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    df_final = pd.DataFrame(lignes_finales)
    sortie   = DOSSIER_SORTIE / f"{fichier.stem}_amex_internet.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export AMEX INTERNET : {sortie.name} ({len(lignes_finales)} écritures)")
