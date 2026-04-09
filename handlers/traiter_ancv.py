import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Optional
from config import DOSSIER_SORTIE
from logger import logger
from core.moniteur_schema import comparer_schema

# ==========================================================
# COLONNES ATTENDUES
# ==========================================================
COL_ETAT        = "EtatANCV"
COL_FINALISE    = "Transaction Finalisée"
COL_MONTANT     = "Montant Commande"
COL_DATE        = "Date de création(UTC)"
COL_REFERENCE   = "Order Id"

# ==========================================================
# UTILITAIRES
# ==========================================================

def nettoyer_montant(val) -> float:
    try:
        return float(str(val).replace(",", ".").replace(" ", "").strip())
    except Exception:
        logger.warning(f"Montant invalide ignoré : {val!r}")
        return 0.0

def formater_date(val) -> Optional[str]:
    """Formate une date au format JJ/MM/AAAA.
    Accepte : date texte, datetime, ou timestamp Unix (secondes).
    """
    # Tentative timestamp Unix
    try:
        v = str(val).strip()
        if v.isdigit():
            d = pd.to_datetime(int(v), unit="s", utc=True)
            return d.strftime("%d/%m/%Y")
    except Exception:
        pass

    # Tentative date texte
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        logger.warning(f"Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d/%m/%Y")

def monter_montant(valeur: float) -> str:
    return f"{abs(valeur):.2f}".replace(".", ",")

def _compte_et_piece(reference: str, date: str) -> tuple[str, str]:
    if len(reference) == 8:
        return "580010DS5", f"ANCV connect Internet du {date}"
    return "580004", f"ANCV connect Caisse du {date}"

def _est_finalise(val: str) -> bool:
    """
    Accepte :
    - 'TRUE' (ancienne valeur)
    - une date non vide (ex: '31/03/2026 10:00:47')
    Refuse :
    - 'FALSE', 'NAN', vide
    """
    v = str(val).strip().upper()
    if v in ("", "NAN", "FALSE", "NONE"):
        return False
    if v == "TRUE":
        return True
    # Si c'est une date parseable → finalisée
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    return not pd.isna(d)

def _est_validated(val: str) -> bool:
    """
    Accepte :
    - 'VALIDATED'
    - 'TRUE' (certains fichiers mettent True dans EtatANCV)
    """
    v = str(val).strip().upper()
    return v in ("VALIDATED", "TRUE")

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_ancv(fichier: Path) -> None:
    """
    Traite un fichier ANCV Connect et génère les écritures comptables.

    Règles métier :
    - Seules les lignes VALIDATED (ou TRUE) + Finalisée (TRUE ou date) + montant > 0
    - Compte selon longueur référence : 8 cars → Internet, sinon Caisse
    - Ligne débit groupée par (date, compte)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier ANCV introuvable : {fichier}")

    logger.info(f"Traitement ANCV : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture et normalisation
    # ----------------------------------------------------------
    df = None
    for sep in ["\t", ";", ","]:
        for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                df_test = pd.read_csv(
                    fichier,
                    sep=sep,
                    dtype=str,
                    encoding=encoding,
                )
                df_test.columns = [c.strip() for c in df_test.columns]
                if COL_ETAT in df_test.columns:
                    df = df_test
                    logger.info(f"Séparateur détecté ({encoding}) : '{sep}'")
                    break
            except Exception as e:
                logger.warning(f"Échec sep='{sep}' encoding='{encoding}' : {e}")
        if df is not None:
            break

    if df is None:
        logger.error(f"Impossible de lire {fichier.name}")
        raise ValueError(f"Fichier illisible : {fichier.name}")

    # ----------------------------------------------------------
    # 1b. Logs de diagnostic
    # ----------------------------------------------------------
    logger.info(f"Colonnes détectées : {list(df.columns)}")
    logger.info(f"Nb lignes brutes : {len(df)}")

    if COL_ETAT in df.columns:
        logger.info(f"Valeurs {COL_ETAT} uniques : {df[COL_ETAT].unique().tolist()}")
    if COL_FINALISE in df.columns:
        logger.info(f"Valeurs {COL_FINALISE} uniques : {df[COL_FINALISE].unique().tolist()}")
    if COL_MONTANT in df.columns:
        logger.info(f"Aperçu montants {COL_MONTANT} : {df[COL_MONTANT].head(5).tolist()}")

    # ----------------------------------------------------------
    # 1c. Vérification colonnes requises
    # ----------------------------------------------------------
    colonnes_requises = {COL_ETAT, COL_FINALISE, COL_MONTANT, COL_DATE, COL_REFERENCE}
    manquantes = colonnes_requises - set(df.columns)
    if manquantes:
        raise ValueError(f"Colonnes manquantes dans {fichier.name} : {manquantes}")

    # ----------------------------------------------------------
    # 1d. Normalisation des montants
    # ----------------------------------------------------------
    df[COL_MONTANT] = df[COL_MONTANT].apply(nettoyer_montant)

    # ----------------------------------------------------------
    # 2. Filtrage métier
    # ----------------------------------------------------------
    masque_etat     = df[COL_ETAT].apply(_est_validated)
    masque_finalise = df[COL_FINALISE].apply(_est_finalise)
    masque_montant  = df[COL_MONTANT] > 0

    logger.info(f"Lignes VALIDATED : {masque_etat.sum()}")
    logger.info(f"Lignes finalisées : {masque_finalise.sum()}")
    logger.info(f"Lignes montant > 0 : {masque_montant.sum()}")

    df = df[masque_etat & masque_finalise & masque_montant].copy()

    if df.empty:
        logger.warning(f"Aucune ligne exploitable dans {fichier.name}")
        return

    # ----------------------------------------------------------
    # 3. Construction des écritures
    # ----------------------------------------------------------
    groupes: dict = defaultdict(lambda: {"lignes": [], "total": 0.0})

    for idx, row in df.iterrows():

        date = formater_date(row[COL_DATE])
        if not date:
            logger.warning(f"Ligne {idx} ignorée : date invalide")
            continue

        reference = str(row[COL_REFERENCE]).strip()
        if not reference or reference.lower() == "nan":
            logger.warning(f"Ligne {idx} ignorée : référence vide")
            continue

        montant       = float(row[COL_MONTANT])
        compte, piece = _compte_et_piece(reference, date)
        cle           = (date, compte)

        groupes[cle]["lignes"].append({
            "STE":        "DLM",
            "DATE":       date,
            "COMPTE":     compte,
            "Auxiliaire": "",
            "n°pièce":    piece,
            "OBJET":      reference,
            "D":          "",
            "C":          monter_montant(montant),
            "Journal":    "CEBOOBA",
            "Analytique": "",
        })

        groupes[cle]["total"] += montant

    # ----------------------------------------------------------
    # 4. Génération finale : une ligne débit par (date, compte)
    # ----------------------------------------------------------
    lignes_finales = []

    for (date, compte), groupe in sorted(groupes.items()):

        lignes_finales.extend(groupe["lignes"])

        total = round(groupe["total"], 2)
        _, piece = _compte_et_piece(
            "12345678" if compte == "580010DS5" else "X",
            date,
        )

        if total == 0.0:
            logger.warning(f"Total nul pour ({date}, {compte}), ligne débit ignorée")
            continue

        lignes_finales.append({
            "STE":        "DLM",
            "DATE":       date,
            "COMPTE":     compte,
            "Auxiliaire": "",
            "n°pièce":    piece,
            "OBJET":      piece,
            "D":          monter_montant(total),
            "C":          "",
            "Journal":    "CEBOOBA",
            "Analytique": "",
        })

    # ----------------------------------------------------------
    # 5. Export CSV
    # ----------------------------------------------------------
    if not lignes_finales:
        logger.warning(f"Aucune écriture générée pour {fichier.name}")
        return

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    df_final = pd.DataFrame(lignes_finales)
    sortie   = DOSSIER_SORTIE / f"{fichier.stem}_ancv.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin-1")

    logger.info(f"Export ANCV : {sortie.name} ({len(lignes_finales)} écritures)")
