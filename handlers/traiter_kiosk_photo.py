import pandas as pd
from pathlib import Path
from typing import Optional
from config import DOSSIER_SORTIE
from logger import logger
from core.moniteur_schema import comparer_schema             # ← AJOUT

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotKioskPhotoFileError(Exception):
    """Levée si aucune vente kiosque photo exploitable n'est trouvée."""
    pass

# ==========================================================
# COLONNES ATTENDUES
# ==========================================================
COL_DATE    = "dateheure"
COL_MONTANT = "montant"
COL_VENDEUR = "vendeur"

COLONNES_REQUISES = [COL_DATE, COL_MONTANT, COL_VENDEUR]

# ==========================================================
# CONSTANTES COMPTABLES
# ==========================================================
STE              = "DLM"
JOURNAL          = "VE"
AUXILIAIRE       = ""
TAUX_TVA         = 1.20

COMPTE_CA        = "706000"
COMPTE_TVA       = "445710"
COMPTE_MONNAYEUR = "580001"
COMPTE_TPE       = "580005"

ANALYTIQUE_CA    = "AD-CO14-XX"
ANALYTIQUE_TVA   = ""
ANALYTIQUE_ENC   = ""

# ==========================================================
# UTILITAIRES
# ==========================================================

def formater_date(val) -> Optional[str]:
    """Formate une date au format JJ/MM/AAAA."""
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        logger.warning(f"Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d/%m/%Y")

def format_montant(valeur: float) -> str:
    """Formate un montant en chaîne comptable française. Ex : 1234.5 → '1234,50'"""
    return f"{abs(valeur):.2f}".replace(".", ",")

def _lire_fichier(fichier: Path) -> pd.DataFrame:
    """Lit le fichier source selon son extension."""
    ext = fichier.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(fichier, sep=";", encoding="utf-8")
    return pd.read_excel(fichier)

def _verifier_colonnes(df: pd.DataFrame, fichier: Path) -> None:
    """Vérifie que les colonnes attendues sont présentes."""
    manquantes = [c for c in COLONNES_REQUISES if c not in df.columns]
    if manquantes:
        raise ValueError(
            f"Colonnes manquantes dans {fichier.name} : {manquantes}\n"
            f"Colonnes trouvées : {list(df.columns)}"
        )

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_kiosk_photo(fichier: Path) -> Path:
    """
    Traite un fichier de ventes du kiosque photo (luge)
    et génère les écritures comptables correspondantes.

    Règles métier :
    - Les ventes JETON sont exclues
    - TVA à 20 % calculée sur le TTC
    - Encaissements ventilés : MONNAYEUR (580001) / TPE (580005)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier kiosque photo introuvable : {fichier}")

    logger.info(f"Traitement KIOSK PHOTO : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture + validation schéma                            # ← MODIFIÉ
    # ----------------------------------------------------------
    df = _lire_fichier(fichier)

    if df.empty:
        raise NotKioskPhotoFileError(f"Fichier vide : {fichier.name}")

    comparer_schema(df, "kiosk_photo")                          # ← AJOUT

    _verifier_colonnes(df, fichier)

    # ----------------------------------------------------------
    # 2. Parcours des ventes
    # ----------------------------------------------------------
    total_ttc        = 0.0
    total_monnayeur  = 0.0
    total_tpe        = 0.0
    date_journee     = None
    nb_ignores       = 0

    for idx, row in df.iterrows():

        # Date de journée = première ligne valide
        if date_journee is None:
            date_journee = formater_date(row[COL_DATE])

        montant_raw = row[COL_MONTANT]

        if pd.isna(montant_raw):
            nb_ignores += 1
            continue

        montant = float(montant_raw)

        if montant == 0:
            nb_ignores += 1
            continue

        vendeur = str(row[COL_VENDEUR]).strip().upper()

        # Ventes jetons exclues
        if "JETON" in vendeur:
            logger.debug(f"Ligne {idx} ignorée : vente JETON")
            nb_ignores += 1
            continue

        total_ttc += montant

        if "MONNAYEUR" in vendeur:
            total_monnayeur += montant
        elif "TPE" in vendeur:
            total_tpe += montant
        else:
            logger.warning(
                f"Ligne {idx} : vendeur non catégorisé {vendeur!r}, "
                f"comptabilisé en TTC uniquement"
            )

    # ----------------------------------------------------------
    # 3. Vérification
    # ----------------------------------------------------------
    if total_ttc == 0:
        raise NotKioskPhotoFileError(
            f"Aucune vente kiosque photo exploitable dans {fichier.name}"
        )

    if not date_journee:
        raise NotKioskPhotoFileError(
            f"Impossible de déterminer la date de journée dans {fichier.name}"
        )

    logger.info(
        f"Kiosk photo : TTC={total_ttc:.2f}€ "
        f"Monnayeur={total_monnayeur:.2f}€ "
        f"TPE={total_tpe:.2f}€ "
        f"({nb_ignores} lignes ignorées)"
    )

    # ----------------------------------------------------------
    # 4. Calculs comptables
    # ----------------------------------------------------------
    ht  = round(total_ttc / TAUX_TVA, 2)
    tva = round(total_ttc - ht, 2)

    piece  = f"JOURNEE DU {date_journee}"
    lignes = []

    # ----------------------------------------------------------
    # 5. Construction des écritures
    # ----------------------------------------------------------

    # Produit CA HT
    lignes.append({
        "STE":        STE,
        "DATE":       date_journee,
        "COMPTE":     COMPTE_CA,
        "Auxiliaire": AUXILIAIRE,
        "n°pièce":    piece,
        "OBJET":      f"{piece} LUGE",
        "D":          "",
        "C":          format_montant(ht),
        "Journal":    JOURNAL,
        "Analytique": ANALYTIQUE_CA,
    })

    # TVA collectée
    lignes.append({
        "STE":        STE,
        "DATE":       date_journee,
        "COMPTE":     COMPTE_TVA,
        "Auxiliaire": AUXILIAIRE,
        "n°pièce":    piece,
        "OBJET":      f"TVA {piece} LUGE",
        "D":          "",
        "C":          format_montant(tva),
        "Journal":    JOURNAL,
        "Analytique": ANALYTIQUE_TVA,
    })

    # Encaissement monnayeur
    if total_monnayeur > 0:
        lignes.append({
            "STE":        STE,
            "DATE":       date_journee,
            "COMPTE":     COMPTE_MONNAYEUR,
            "Auxiliaire": AUXILIAIRE,
            "n°pièce":    piece,
            "OBJET":      f"{piece} LUGE - MONNAYEUR",
            "D":          format_montant(total_monnayeur),
            "C":          "",
            "Journal":    JOURNAL,
            "Analytique": ANALYTIQUE_ENC,
        })

    # Encaissement TPE
    if total_tpe > 0:
        lignes.append({
            "STE":        STE,
            "DATE":       date_journee,
            "COMPTE":     COMPTE_TPE,
            "Auxiliaire": AUXILIAIRE,
            "n°pièce":    piece,
            "OBJET":      f"{piece} LUGE - TPE",
            "D":          format_montant(total_tpe),
            "C":          "",
            "Journal":    JOURNAL,
            "Analytique": ANALYTIQUE_ENC,
        })

    # ----------------------------------------------------------
    # 6. Export CSV
    # ----------------------------------------------------------
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    df_final = pd.DataFrame(lignes, columns=[
        "STE", "DATE", "COMPTE", "Auxiliaire",
        "n°pièce", "OBJET", "D", "C",
        "Journal", "Analytique"
    ])

    sortie = DOSSIER_SORTIE / f"{fichier.stem}_kiosk_photo.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export KIOSK PHOTO : {sortie.name} ({len(lignes)} écritures)")
    return sortie
