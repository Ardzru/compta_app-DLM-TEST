import pandas as pd
import re
from pathlib import Path
from config import DOSSIER_SORTIE


# Exception levée si aucune ligne TA exploitable n’est trouvée
class NotTAFileError(Exception):
    pass


# ------------------------------------------------------------
# UTILITAIRES
# ------------------------------------------------------------

def nettoyer_commande(val):
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


def formater_date(val):
    """
    Formate une date au format JJ/MM/AAAA.
    Utilisée pour la date comptable et les libellés.
    """
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        return None

    return d.strftime("%d/%m/%Y")


# ------------------------------------------------------------
# TRAITEMENT PRINCIPAL
# ------------------------------------------------------------

def traiter_ta(fichier: Path):
    """
    Traite un fichier TA (billetterie / caisse) et génère
    les écritures comptables correspondantes.
    """
    # Lecture du fichier Excel TA
    df = pd.read_excel(fichier)

    # Noms des colonnes du fichier TA
    COL_DATE = "DATE"
    COL_COMMANDE = "VALEUR PROMPT"
    COL_CAISSE = "CAISSE"
    COL_MONTANT = "MONTANT"
    COL_LIBELLE = "SZNAME"

    # Caisses autorisées pour le traitement
    CAISSES_AUTORISEES = {"72", "73", "77"}

    # Libellés correspondant à des ventes
    VENTES = {
        "Vente d'un titre",
        "Vente d'un article",
        "Prêt"
    }

    # Libellés correspondant à des annulations
    ANNULATIONS = {
        "Annulation automatique",
        "Annulation article"
    }

    # Structures de cumul
    commandes = {}   # Par numéro de commande
    caisses = {}     # Par caisse
    date_source = None

    # ------------------------------------------------------------
    # LECTURE DES LIGNES DU FICHIER
    # ------------------------------------------------------------

    for _, row in df.iterrows():

        # Détermination de la date de la journée (première date valide)
        if date_source is None and not pd.isna(row[COL_DATE]):
            date_source = formater_date(row[COL_DATE])

        # Filtrage des caisses non autorisées
        caisse = str(row[COL_CAISSE]).strip()
        if caisse not in CAISSES_AUTORISEES:
            continue

        # Extraction du numéro de commande
        commande = nettoyer_commande(row[COL_COMMANDE])
        if not commande:
            continue

        montant = float(row[COL_MONTANT])
        libelle = str(row[COL_LIBELLE]).strip()

        # Initialisation des structures si nécessaire
        commandes.setdefault(commande, {"date": date_source, "D": 0, "C": 0})
        caisses.setdefault(caisse, {"ventes": 0, "annulations": 0})

        # 🔁 LOGIQUE COMMANDE (INVERSE)
        # Les ventes alimentent le débit
        # Les annulations alimentent le crédit
        if libelle in VENTES:
            commandes[commande]["D"] += montant
            caisses[caisse]["ventes"] += montant

        elif libelle in ANNULATIONS:
            commandes[commande]["C"] += montant
            caisses[caisse]["annulations"] += montant

    # Aucun mouvement TA détecté
    if not commandes:
        raise NotTAFileError("Aucune ligne TA détectée")

    piece_journee = f"JOURNEE DU {date_source}"
    lignes = []

    # ------------------------------------------------------------
    # LIGNES PAR NUMÉRO DE COMMANDE
    # ------------------------------------------------------------

    for commande, data in commandes.items():

        # Ligne débit (ventes)
        if data["D"] > 0:
            lignes.append({
                "STE": "DLM",
                "DATE": data["date"],
                "COMPTE": "580010DS5",
                "Auxiliaire": "",
                "n°pièce": piece_journee,
                "OBJET": commande,
                "D": f"{data['D']:.2f}".replace(".", ","),
                "C": "",
                "Journal": "VE",
                "Analytique": ""
            })

        # Ligne crédit (annulations)
        if data["C"] > 0:
            lignes.append({
                "STE": "DLM",
                "DATE": data["date"],
                "COMPTE": "580010DS5",
                "Auxiliaire": "",
                "n°pièce": piece_journee,
                "OBJET": commande,
                "D": "",
                "C": f"{data['C']:.2f}".replace(".", ","),
                "Journal": "VE",
                "Analytique": ""
            })

    # ------------------------------------------------------------
    # LIGNES VIA (CAISSES)
    # ------------------------------------------------------------

    for caisse, totaux in caisses.items():

        # Différence ventes / annulations par caisse
        diff = totaux["ventes"] - totaux["annulations"]
        if diff == 0:
            continue

        lignes.append({
            "STE": "DLM",
            "DATE": date_source,
            "COMPTE": "580010DS5",
            "Auxiliaire": "",
            "n°pièce": piece_journee,
            "OBJET": f"JOURNEE DU {date_source.replace('/', '-')} CAISSE {caisse}",
            "D": f"{abs(diff):.2f}".replace(".", ",") if diff < 0 else "",
            "C": f"{diff:.2f}".replace(".", ",") if diff > 0 else "",
            "Journal": "VE",
            "Analytique": ""
        })

    # ------------------------------------------------------------
    # EXPORT DU FICHIER COMPTABLE
    # ------------------------------------------------------------

    df_final = pd.DataFrame(lignes, columns=[
        "STE", "DATE", "COMPTE", "Auxiliaire",
        "n°pièce", "OBJET", "D", "C",
        "Journal", "Analytique"
    ])

    sortie = DOSSIER_SORTIE / f"{fichier.stem}_ta.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    return sortie
