import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Optional
from config import DOSSIER_SORTIE
from config import logger
from core.utils.montant import to_float, format_montant
from core.utils.date import formater_date
from core.utils.colonnes import STE_DEFAUT, JOURNAUX, COLONNES_SORTIE


# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotAncvFileError(Exception):
    """Levée si aucune ligne ANCV exploitable n'est trouvée."""
    pass


# ==========================================================
# COLONNES ATTENDUES
# ==========================================================
COL_ETAT = "EtatANCV"
COL_FINALISE = "Transaction Finalisée"
COL_MONTANT = "CVCo"
COL_DATE = "Date de création(UTC)"
COL_REFERENCE = "Order Id"


# ==========================================================
# UTILITAIRES PRIVÉS
# ==========================================================

def _compte_et_piece(reference: str, date: str) -> tuple:
    """
    Order Id à 8 chiffres → Internet, sinon Caisse.

    Returns:
        tuple: (compte, piece)
    """
    ref_clean = str(reference).strip()
    if len(ref_clean) == 8 and ref_clean.isdigit():
        return "580010DS5", f"ANCV connect Internet du {date}"
    return "580004", f"ANCV connect Caisse du {date}"


def _est_finalise(val) -> bool:
    """Détecte si une transaction est finalisée."""
    v = str(val).strip().upper()
    if v in ("", "NAN", "FALSE", "NONE"):
        return False
    if v == "TRUE":
        return True
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    return not pd.isna(d)


def _est_validated(val) -> bool:
    """Détecte si une ligne est validée."""
    v = str(val).strip().upper()
    return v in ("VALIDATED", "TRUE")


def _corriger_fichier_ancv(fichier: Path) -> pd.DataFrame:
    """
    Corrige le fichier ANCV qui a 12 colonnes au lieu de 11.
    Supprime les `;` finaux et les colonnes vides.
    """
    with open(fichier, 'r', encoding='utf-8-sig') as f:
        lignes = f.readlines()

    # Supprimer le ; final de chaque ligne
    lignes_corrigees = []
    for ligne in lignes:
        ligne = ligne.rstrip()
        if ligne.endswith(';'):
            ligne = ligne[:-1]
        lignes_corrigees.append(ligne)

    # Écrire dans un fichier temporaire
    fichier_temp = fichier.with_suffix('.csv.temp')
    with open(fichier_temp, 'w', encoding='utf-8-sig') as f:
        f.write('\n'.join(lignes_corrigees))

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

    fichier_temp.unlink()
    return df


# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_ancv(fichier: Path) -> Optional[Path]:
    """
    Traite un fichier ANCV et génère les écritures comptables.

    Règles métier :
    - Filtrage : VALIDATED + Finalisée + Montant > 0
    - Groupement par date et compte
    - Export CSV

    Returns:
        Path: Chemin du fichier généré, ou None si aucune écriture
    """
    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier ANCV introuvable : {fichier}")

    logger.info(f"Traitement ANCV : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture avec correction du fichier
    # ----------------------------------------------------------
    try:
        df = _corriger_fichier_ancv(fichier)
    except Exception as e:
        logger.error(f"Échec de la correction du fichier : {e}")
        raise ValueError(f"Échec de la correction du fichier : {e}")

    # ----------------------------------------------------------
    # 2. Vérification colonnes requises
    # ----------------------------------------------------------
    colonnes_requises = {COL_ETAT, COL_FINALISE, COL_MONTANT,
                         COL_DATE, COL_REFERENCE}
    manquantes = colonnes_requises - set(df.columns)
    if manquantes:
        logger.error(f"Colonnes manquantes : {manquantes}")
        raise ValueError(
            f"Colonnes manquantes dans {fichier.name} : {manquantes}"
        )

    logger.info(f"Colonnes trouvées : {list(df.columns)}")

    # ----------------------------------------------------------
    # 3. Filtrage des lignes
    # ----------------------------------------------------------
    df_initial = len(df)

    # Filtrer les lignes validées
    df = df[df[COL_ETAT].apply(_est_validated)]
    logger.info(f"  Initial       : {df_initial} lignes")
    logger.info(f"  VALIDATED     : {len(df)} lignes")

    # Filtrer les lignes finalisées
    df = df[df[COL_FINALISE].apply(_est_finalise)]
    logger.info(f"  Finalisées    : {len(df)} lignes")

    # Convertir et filtrer montants > 0
    df[COL_MONTANT] = df[COL_MONTANT].apply(to_float)
    df = df[df[COL_MONTANT] > 0]
    logger.info(f"  Montant > 0   : {len(df)} lignes")

    if len(df) == 0:
        logger.warning(f"⚠️ Aucune ligne valide dans {fichier.name}")
        raise NotAncvFileError(f"Aucune ligne ANCV exploitable dans {fichier.name}")

    # ----------------------------------------------------------
    # 4. Groupement par (date, compte)
    # ----------------------------------------------------------
    groupes = defaultdict(lambda: {"lignes": [], "total": 0.0})

    for idx, row in df.iterrows():
        date = formater_date(row[COL_DATE])
        if not date:
            logger.warning(f"Ligne {idx} ignorée : date invalide")
            continue

        montant = to_float(row[COL_MONTANT])
        reference = str(row[COL_REFERENCE]).strip()

        # Déterminer le compte et la pièce
        compte, piece = _compte_et_piece(reference, date)

        # Ajouter la ligne au groupe
        groupes[(date, compte)]["lignes"].append({
            "STE": STE_DEFAUT,
            "DATE": date,
            "COMPTE": compte,
            "Auxiliaire": "",
            "n°pièce": piece,
            "OBJET": reference,
            "D": "",
            "C": format_montant(montant),
            "Journal": JOURNAUX["ancv"],
            "Analytique": "",
        })

        groupes[(date, compte)]["total"] += montant

    # ----------------------------------------------------------
    # 5. Génération des lignes finales
    # ----------------------------------------------------------
    lignes_finales = []

    for (date, compte), groupe in sorted(groupes.items()):
        lignes_finales.extend(groupe["lignes"])

        total = round(groupe["total"], 2)
        if total == 0.0:
            logger.warning(f"Total nul pour ({date}, {compte}), ligne banque ignorée")
            continue

        # Ligne banque (DÉBIT)
        _, piece = _compte_et_piece(
            "12345678" if compte == "580010DS5" else "X",
            date,
        )

        lignes_finales.append({
            "STE": STE_DEFAUT,
            "DATE": date,
            "COMPTE": compte,
            "Auxiliaire": "",
            "n°pièce": piece,
            "OBJET": piece,
            "D": format_montant(total),
            "C": "",
            "Journal": JOURNAUX["ancv"],
            "Analytique": "",
        })

    # ----------------------------------------------------------
    # 6. Export CSV
    # ----------------------------------------------------------
    if not lignes_finales:
        logger.warning(f"⚠️ Aucune écriture générée pour {fichier.name}")
        raise NotAncvFileError(f"Aucune écriture générée pour {fichier.name}")

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    df_final = pd.DataFrame(lignes_finales)
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_ancv.csv"

    df_final.to_csv(
        sortie,
        sep=";",
        index=False,
        encoding="latin-1",
        columns=COLONNES_SORTIE
    )

    logger.info(
        f"✅ Export ANCV : {sortie.name} ({len(lignes_finales)} écritures)"
    )
    return sortie


# ==========================================================
# CLASSE HANDLER
# ==========================================================

class TraiterTraiterAncvHandler:
    """Handler pour traiter les fichiers Traiter Ancv."""

    @staticmethod
    def traiter(fichier: Path) -> None:
        """Traite un fichier traiter_ancv."""
        traiter_ancv(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """Vérifie si c'est un fichier traiter_ancv."""
        return detecteur_result.get("type") == "traiter_ancv"


__all__ = ['TraiterTraiterAncvHandler', 'traiter_ancv']


# ==========================================================
# CLASSE HANDLER
# ==========================================================

class TraiterAncvHandler:
    """Handler pour traiter les fichiers ancv."""

    @staticmethod
    def traiter(fichier: Path) -> None:
        """Traite un fichier ancv."""
        traiter_ancv(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """Vérifie si c'est un fichier ancv."""
        return detecteur_result.get("type") == "ancv"


__all__ = ['TraiterAncvHandler', 'traiter_ancv']
