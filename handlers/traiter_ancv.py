import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Optional
from config import DOSSIER_SORTIE
from logger import logger

# ==========================================================
# COLONNES ATTENDUES
# ==========================================================
COL_ETAT        = "EtatANCV"
COL_FINALISE    = "Transaction Finalisée"
COL_MONTANT     = "CVCo"
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
    """Formate une date au format JJ/MM/AAAA."""
    try:
        v = str(val).strip()
        if not v or v.upper() in ("NAN", "NONE"):
            return None
        d = pd.to_datetime(v, dayfirst=True, errors="coerce")
        if not pd.isna(d):
            return d.strftime("%d/%m/%Y")
        logger.warning(f"Date invalide ignorée : {val!r}")
        return None
    except Exception:
        logger.warning(f"Date invalide ignorée : {val!r}")
        return None

def monter_montant(valeur: float) -> str:
    return f"{abs(valeur):.2f}".replace(".", ",")

def _compte_et_piece(reference: str, date: str) -> tuple[str, str]:
    """Order Id à 8 chiffres → Internet, sinon Caisse."""
    ref_clean = str(reference).strip()
    if len(ref_clean) == 8 and ref_clean.isdigit():
        return "580010DS5", f"ANCV connect Internet du {date}"
    return "580004", f"ANCV connect Caisse du {date}"

def _est_finalise(val: str) -> bool:
    v = str(val).strip().upper()
    if v in ("", "NAN", "FALSE", "NONE"):
        return False
    if v == "TRUE":
        return True
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    return not pd.isna(d)

def _est_validated(val: str) -> bool:
    v = str(val).strip().upper()
    return v in ("VALIDATED", "TRUE")

# ==========================================================
# CORRECTION DU FICHIER AVEC 12 COLONNES
# ==========================================================

def corriger_fichier_ancv(fichier: Path) -> pd.DataFrame:
    """Corrige le fichier ANCV qui a 12 colonnes au lieu de 11."""
    with open(fichier, 'r', encoding='utf-8-sig') as f:
        lignes = f.readlines()

    # Supprimer le ; final de chaque ligne
    lignes_corrigées = []
    for ligne in lignes:
        ligne = ligne.rstrip()
        if ligne.endswith(';'):
            ligne = ligne[:-1]  # Supprimer le dernier ;
        lignes_corrigées.append(ligne)

    # Écrire dans un fichier temporaire
    fichier_temp = fichier.with_suffix('.csv.temp')
    with open(fichier_temp, 'w', encoding='utf-8-sig') as f:
        f.write('\n'.join(lignes_corrigées))

    # Lire avec pandas
    df = pd.read_csv(
        fichier_temp,
        sep=';',
        dtype=str,
        encoding='utf-8-sig'
    )

    # Supprimer la colonne vide créée par le ; final
    if 'Unnamed: 11' in df.columns:
        df = df.drop(columns=['Unnamed: 11'])

    # Supprimer les lignes vides
    df = df.dropna(how='all')

    fichier_temp.unlink()  # Supprimer le fichier temporaire
    return df

# ==========================================================
# TRAITEMENT ANCV
# ==========================================================

def traiter_ancv(fichier: Path) -> None:
    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier ANCV introuvable : {fichier}")

    logger.info(f"Traitement ANCV : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture avec correction du fichier
    # ----------------------------------------------------------
    try:
        df = corriger_fichier_ancv(fichier)
    except Exception as e:
        raise ValueError(f"Échec de la correction du fichier : {e}")

    # ----------------------------------------------------------
    # 2. Vérification colonnes requises
    # ----------------------------------------------------------
    colonnes_requises = {COL_ETAT, COL_FINALISE, COL_MONTANT,
                         COL_DATE, COL_REFERENCE}
    manquantes = colonnes_requises - set(df.columns)
    if manquantes:
        raise ValueError(
            f"Colonnes manquantes dans {fichier.name} : {manquantes}"
        )

    # ----------------------------------------------------------
    # 3. Debug valeurs clés
    # ----------------------------------------------------------
    logger.info(f"Colonnes après correction : {list(df.columns)}")
    logger.info(f"  [Date de création(UTC)] exemples : {df[COL_DATE].head(3).tolist()}")
    logger.info(f"  [Order Id] exemples : {df[COL_REFERENCE].head(3).tolist()}")
    logger.info(f"  [CVCo] exemples : {df[COL_MONTANT].head(3).tolist()}")

    # ----------------------------------------------------------
    # 4. Filtrage des lignes
    # ----------------------------------------------------------
    # Filtrer les lignes validées
    df = df[df[COL_ETAT].apply(_est_validated)]
    logger.info(f"VALIDATED   : {len(df)}")

    # Filtrer les lignes finalisées
    df = df[df[COL_FINALISE].apply(_est_finalise)]
    logger.info(f"Finalisées  : {len(df)}")

    # Filtrer les lignes avec montant > 0
    df[COL_MONTANT] = df[COL_MONTANT].apply(nettoyer_montant)
    df = df[df[COL_MONTANT] > 0]
    logger.info(f"Montant > 0 : {len(df)}")

    if len(df) == 0:
        logger.warning(f"Aucune ligne valide dans {fichier.name}")
        return

    # ----------------------------------------------------------
    # 5. Groupement par date et compte
    # ----------------------------------------------------------
    groupes = defaultdict(lambda: {"lignes": [], "total": 0.0})

    for _, row in df.iterrows():
        date = formater_date(row[COL_DATE])
        if not date:
            logger.warning(f"Ligne {row['ID']} ignorée : date invalide")
            continue

        montant = nettoyer_montant(row[COL_MONTANT])
        reference = str(row[COL_REFERENCE]).strip()

        # Déterminer le compte et la pièce
        compte, piece = _compte_et_piece(reference, date)

        # Ajouter la ligne au groupe
        groupes[(date, compte)]["lignes"].append({
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

        groupes[(date, compte)]["total"] += montant

    # ----------------------------------------------------------
    # 6. Génération des lignes finales
    # ----------------------------------------------------------
    lignes_finales = []

    for (date, compte), groupe in sorted(groupes.items()):
        lignes_finales.extend(groupe["lignes"])

        total = round(groupe["total"], 2)
        if total == 0.0:
            logger.warning(f"Total nul pour ({date}, {compte}), ignoré")
            continue

        _, piece = _compte_et_piece(
            "12345678" if compte == "580010DS5" else "X",
            date,
        )

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
    # 7. Export CSV
    # ----------------------------------------------------------
    if not lignes_finales:
        logger.warning(f"Aucune écriture générée pour {fichier.name}")
        return

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    df_final = pd.DataFrame(lignes_finales)
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_ancv.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin-1")

    logger.info(
        f"Export ANCV : {sortie.name} ({len(lignes_finales)} écritures)"
    )
