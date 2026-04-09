import re
import pandas as pd
from pathlib import Path
from typing import Optional
from config import DOSSIER_SORTIE
from logger import logger
from core.moniteur_schema import comparer_schema             # ← AJOUT

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotTAFileError(Exception):
    """Levée si aucune ligne TA exploitable n'est trouvée."""
    pass

# ==========================================================
# COLONNES ATTENDUES
# ==========================================================
COL_DATE     = "DATE"
COL_COMMANDE = "VALEUR PROMPT"
COL_CAISSE   = "CAISSE"
COL_MONTANT  = "MONTANT"
COL_LIBELLE  = "SZNAME"

COLONNES_REQUISES = [COL_DATE, COL_COMMANDE, COL_CAISSE, COL_MONTANT, COL_LIBELLE]

# ==========================================================
# CONSTANTES MÉTIER
# ==========================================================
CAISSES_AUTORISEES = {"72", "73", "77"}

LIBELLES_VENTES = {
    "Vente d'un titre",
    "Vente d'un article",
    "Prêt",
}

LIBELLES_ANNULATIONS = {
    "Annulation automatique",
    "Annulation article",
}

# ==========================================================
# CONSTANTES COMPTABLES
# ==========================================================
STE        = "DLM"
COMPTE     = "580010DS5"
JOURNAL    = "VE"
AUXILIAIRE = ""
ANALYTIQUE = ""

# ==========================================================
# UTILITAIRES
# ==========================================================

def _nettoyer_commande(val) -> Optional[str]:
    """
    Extrait et normalise le numéro de commande.
    - Conserve uniquement les chiffres
    - Nécessite au moins 8 chiffres
    - Retourne les 8 premiers chiffres
    """
    if pd.isna(val):
        return None
    chiffres = re.findall(r"\d", str(val))
    if len(chiffres) < 8:
        return None
    return "".join(chiffres[:8])

def _formater_date(val) -> Optional[str]:
    """Formate une date au format JJ/MM/AAAA."""
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        logger.warning(f"Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d/%m/%Y")

def format_montant(valeur: float) -> str:
    """Formate un montant en chaîne comptable française. Ex : 1234.5 → '1234,50'"""
    return f"{abs(valeur):.2f}".replace(".", ",")

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

def traiter_ta(fichier: Path) -> Path:
    """
    Traite un fichier TA (billetterie / caisse) et génère
    les écritures comptables correspondantes.

    Règles métier :
    - Seules les caisses 72, 73, 77 sont traitées
    - Ventes → Débit 580010DS5
    - Annulations → Crédit 580010DS5
    - Contrepartie par caisse (diff ventes - annulations)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier TA introuvable : {fichier}")

    logger.info(f"Traitement TA : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture + validation schéma                            # ← MODIFIÉ
    # ----------------------------------------------------------
    df = pd.read_excel(fichier)

    if df.empty:
        raise NotTAFileError(f"Fichier vide : {fichier.name}")

    comparer_schema(df, "ta")                                   # ← AJOUT

    _verifier_colonnes(df, fichier)

    # ----------------------------------------------------------
    # 2. Parcours des lignes
    # ----------------------------------------------------------
    commandes: dict = {}   # { num_commande: {"date": str, "D": float, "C": float} }
    caisses:   dict = {}   # { caisse: {"ventes": float, "annulations": float} }
    date_source: Optional[str] = None
    nb_ignores = 0

    for idx, row in df.iterrows():

        # Date de journée = première date valide rencontrée
        if date_source is None and not pd.isna(row[COL_DATE]):
            date_source = _formater_date(row[COL_DATE])

        # Filtrage caisse
        caisse = str(row[COL_CAISSE]).strip()
        if caisse not in CAISSES_AUTORISEES:
            nb_ignores += 1
            continue

        # Numéro de commande
        commande = _nettoyer_commande(row[COL_COMMANDE])
        if not commande:
            logger.debug(f"Ligne {idx} ignorée : commande invalide {row[COL_COMMANDE]!r}")
            nb_ignores += 1
            continue

        # Montant
        montant_raw = row[COL_MONTANT]
        if pd.isna(montant_raw):
            nb_ignores += 1
            continue
        montant = float(montant_raw)

        libelle = str(row[COL_LIBELLE]).strip()

        # Initialisation des accumulateurs
        commandes.setdefault(commande, {"date": date_source, "D": 0.0, "C": 0.0})
        caisses.setdefault(caisse, {"ventes": 0.0, "annulations": 0.0})

        if libelle in LIBELLES_VENTES:
            commandes[commande]["D"] += montant
            caisses[caisse]["ventes"] += montant

        elif libelle in LIBELLES_ANNULATIONS:
            commandes[commande]["C"] += montant
            caisses[caisse]["annulations"] += montant

        else:
            logger.debug(f"Ligne {idx} : libellé non catégorisé {libelle!r}")
            nb_ignores += 1

    # ----------------------------------------------------------
    # 3. Vérification
    # ----------------------------------------------------------
    if not commandes:
        raise NotTAFileError(
            f"Aucune ligne TA exploitable dans {fichier.name}"
        )

    if not date_source:
        raise NotTAFileError(
            f"Impossible de déterminer la date de journée dans {fichier.name}"
        )

    logger.info(
        f"TA : {len(commandes)} commandes, "
        f"{len(caisses)} caisses, "
        f"{nb_ignores} lignes ignorées"
    )

    # ----------------------------------------------------------
    # 4. Construction des écritures
    # ----------------------------------------------------------
    piece  = f"JOURNEE DU {date_source}"
    lignes = []

    # Lignes par commande
    for commande, data in commandes.items():

        if data["D"] > 0:
            lignes.append({
                "STE":        STE,
                "DATE":       data["date"],
                "COMPTE":     COMPTE,
                "Auxiliaire": AUXILIAIRE,
                "n°pièce":    piece,
                "OBJET":      commande,
                "D":          format_montant(data["D"]),
                "C":          "",
                "Journal":    JOURNAL,
                "Analytique": ANALYTIQUE,
            })

        if data["C"] > 0:
            lignes.append({
                "STE":        STE,
                "DATE":       data["date"],
                "COMPTE":     COMPTE,
                "Auxiliaire": AUXILIAIRE,
                "n°pièce":    piece,
                "OBJET":      commande,
                "D":          "",
                "C":          format_montant(data["C"]),
                "Journal":    JOURNAL,
                "Analytique": ANALYTIQUE,
            })

    # Lignes de contrepartie par caisse
    for caisse, totaux in caisses.items():

        diff = totaux["ventes"] - totaux["annulations"]

        if diff == 0:
            logger.debug(f"Caisse {caisse} équilibrée, pas de contrepartie")
            continue

        objet = f"JOURNEE DU {date_source.replace('/', '-')} CAISSE {caisse}"

        lignes.append({
            "STE":        STE,
            "DATE":       date_source,
            "COMPTE":     COMPTE,
            "Auxiliaire": AUXILIAIRE,
            "n°pièce":    piece,
            "OBJET":      objet,
            "D":          format_montant(diff) if diff < 0 else "",
            "C":          format_montant(diff) if diff > 0 else "",
            "Journal":    JOURNAL,
            "Analytique": ANALYTIQUE,
        })

    # ----------------------------------------------------------
    # 5. Export CSV
    # ----------------------------------------------------------
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    df_final = pd.DataFrame(lignes, columns=[
        "STE", "DATE", "COMPTE", "Auxiliaire",
        "n°pièce", "OBJET", "D", "C",
        "Journal", "Analytique"
    ])

    sortie = DOSSIER_SORTIE / f"{fichier.stem}_ta.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(f"Export TA : {sortie.name} ({len(lignes)} écritures)")
    return sortie
