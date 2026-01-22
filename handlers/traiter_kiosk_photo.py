import pandas as pd
from pathlib import Path
from config import DOSSIER_SORTIE


# Exception levée si aucune vente kiosque photo exploitable n’est trouvée
class NotKioskPhotoFileError(Exception):
    pass


def formater_date(val):
    """
    Formate une date au format JJ/MM/AAAA.
    Le fichier kiosque photo utilise un format jour en premier.
    """
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        return None
    return d.strftime("%d/%m/%Y")


def traiter_kiosk_photo(fichier: Path):
    """
    Traite un fichier de ventes du kiosque photo (luge)
    et génère les écritures comptables correspondantes.
    """

    # ------------------------------------------------------------
    # LECTURE DU FICHIER SOURCE
    # ------------------------------------------------------------

    # Lecture adaptée selon le type de fichier
    if fichier.suffix.lower() == ".csv":
        df = pd.read_csv(fichier, sep=";", encoding="utf-8")
    else:
        df = pd.read_excel(fichier)

    # Noms des colonnes du fichier kiosque photo
    COL_DATE = "dateheure"
    COL_MONTANT = "montant"
    COL_VENDEUR = "vendeur"

    # Totaux cumulés
    total_ttc = 0.0
    total_monnayeur = 0.0
    total_tpe = 0.0
    date_journee = None

    # ------------------------------------------------------------
    # PARCOURS DES VENTES
    # ------------------------------------------------------------

    for _, row in df.iterrows():

        # Détermination de la date de la journée (première ligne valide)
        if date_journee is None:
            date_journee = formater_date(row[COL_DATE])

        montant = row[COL_MONTANT]
        if pd.isna(montant) or float(montant) == 0:
            continue

        vendeur = str(row[COL_VENDEUR]).upper()

        # ❌ Les ventes par jetons ne sont pas comptabilisées
        if "JETON" in vendeur:
            continue

        # Cumul du chiffre d’affaires TTC
        total_ttc += float(montant)

        # Répartition par mode de paiement
        if "MONNAYEUR" in vendeur:
            total_monnayeur += float(montant)
        elif "TPE" in vendeur:
            total_tpe += float(montant)

    # Aucune vente détectée → fichier non conforme
    if total_ttc == 0:
        raise NotKioskPhotoFileError("Aucune vente kiosque photo détectée")

    # ------------------------------------------------------------
    # CALCULS COMPTABLES
    # ------------------------------------------------------------

    # Calcul HT et TVA (TVA à 20 %)
    ht = round(total_ttc / 1.20, 2)
    tva = round(total_ttc - ht, 2)

    piece = f"JOURNEE DU {date_journee}"
    lignes = []

    # ------------------------------------------------------------
    # ÉCRITURES COMPTABLES
    # ------------------------------------------------------------

    # 🔹 Produit (chiffre d’affaires HT)
    lignes.append({
        "STE": "DLM",
        "DATE": date_journee,
        "COMPTE": "706000",
        "Auxiliaire": "",
        "n°pièce": piece,
        "OBJET": f"{piece} LUGE",
        "D": "",
        "C": f"{ht:.2f}".replace(".", ","),
        "Journal": "VE",
        "Analytique": "AD-CO14-XX"
    })

    # 🔹 TVA collectée
    lignes.append({
        "STE": "DLM",
        "DATE": date_journee,
        "COMPTE": "445710",
        "Auxiliaire": "",
        "n°pièce": piece,
        "OBJET": f"TVA {piece} LUGE",
        "D": "",
        "C": f"{tva:.2f}".replace(".", ","),
        "Journal": "VE",
        "Analytique": ""
    })

    # 🔹 Encaissement monnayeur (580001)
    if total_monnayeur > 0:
        lignes.append({
            "STE": "DLM",
            "DATE": date_journee,
            "COMPTE": "580001",
            "Auxiliaire": "",
            "n°pièce": piece,
            "OBJET": f"{piece} LUGE - MONNAYEUR",
            "D": f"{total_monnayeur:.2f}".replace(".", ","),
            "C": "",
            "Journal": "VE",
            "Analytique": ""
        })

    # 🔹 Encaissement TPE (580005)
    if total_tpe > 0:
        lignes.append({
            "STE": "DLM",
            "DATE": date_journee,
            "COMPTE": "580005",
            "Auxiliaire": "",
            "n°pièce": piece,
            "OBJET": f"{piece} LUGE - TPE",
            "D": f"{total_tpe:.2f}".replace(".", ","),
            "C": "",
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

    sortie = DOSSIER_SORTIE / f"{fichier.stem}_kiosk_photo.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    return sortie
