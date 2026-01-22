import pandas as pd
from pathlib import Path
from config import DOSSIER_SORTIE


# Exception levée si le fichier ne contient aucune ligne ALMA exploitable
class NotAlmaFileError(Exception):
    pass


def nettoyer_montant(val):
    """
    Nettoie et convertit un montant issu du fichier ALMA.
    - Gère les valeurs vides
    - Supprime les séparateurs
    - Convertit en float
    - Division par 100 (format ALMA en centimes)
    """
    if pd.isna(val):
        return 0.0

    s = str(val)
    s = s.replace(".", "").replace("-", "").replace(",", ".").strip()

    try:
        return float(s) / 100
    except ValueError:
        return 0.0


def formater_date(val, jours_a_ajouter=0):
    """
    Formate une date au format JJ/MM/AAAA.
    Utilisée pour le libellé de la pièce.
    """
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        return None
    return d.strftime("%d/%m/%Y")


def formater_date_ecriture(val, jours_a_ajouter=8):
    """
    Calcule la date d’écriture comptable.
    Par défaut : date ALMA + 8 jours.
    """
    d = pd.to_datetime(val, errors="coerce")
    if pd.isna(d):
        return None

    d = d + pd.Timedelta(days=jours_a_ajouter)
    return d.strftime("%d/%m/%Y")


def traiter_alma(fichier: Path):
    """
    Traite un fichier ALMA et génère les écritures comptables correspondantes.
    """
    # Lecture du fichier Excel ALMA
    df = pd.read_excel(fichier)

    # Index des colonnes ALMA (basé sur le format fournisseur)
    COL_DATE = 1          # Date de transaction (colonne B)
    COL_MONTANT = 2       # Montant total (colonne C/D selon export)
    COL_TVA = 4           # TVA (colonne E)
    COL_FRAIS = 5         # Frais ALMA (colonne F)
    COL_REFERENCE = 11    # Référence transaction

    lignes = []

    # Parcours ligne par ligne du fichier ALMA
    for _, row in df.iterrows():

        # Dates
        date_lib = formater_date(row.iloc[COL_DATE])
        date_ecriture = formater_date_ecriture(row.iloc[COL_DATE])

        # Si la date est invalide, on ignore la ligne
        if not date_ecriture or not date_lib:
            continue

        # Montants
        montant_achat = nettoyer_montant(row.iloc[COL_MONTANT])
        tva = nettoyer_montant(row.iloc[COL_TVA])
        frais = nettoyer_montant(row.iloc[COL_FRAIS])
        reference = str(row.iloc[COL_REFERENCE]).strip()

        # Ligne vide ou non exploitable
        if montant_achat == 0 and tva == 0 and frais == 0:
            continue

        # Calcul du montant réellement encaissé
        difference = montant_achat - (tva + frais)

        objet = f"ALMA {date_lib}"

        # Écriture 1 : Montant total de la vente (crédit compte ALMA)
        lignes.append({
            "STE": "DLM",
            "DATE": date_ecriture,
            "COMPTE": "580010DS5",
            "Auxiliaire": "",
            "n°pièce": objet,
            "OBJET": reference,
            "D": "",
            "C": f"{montant_achat:.2f}".replace(".", ","),
            "Journal": "CEBOOBA",
            "Analytique": ""
        })

        # Écriture 2 : TVA collectée
        lignes.append({
            "STE": "DLM",
            "DATE": date_ecriture,
            "COMPTE": "445660",
            "Auxiliaire": "",
            "n°pièce": objet,
            "OBJET": f"TVA {objet}",
            "D": f"{tva:.2f}".replace(".", ","),
            "C": "",
            "Journal": "CEBOOBA",
            "Analytique": ""
        })

        # Écriture 3 : Frais ALMA
        lignes.append({
            "STE": "DLM",
            "DATE": date_ecriture,
            "COMPTE": "627800",
            "Auxiliaire": "",
            "n°pièce": objet,
            "OBJET": f"Frais {objet}",
            "D": f"{frais:.2f}".replace(".", ","),
            "C": "",
            "Journal": "CEBOOBA",
            "Analytique": "ST-CT00-XX"
        })

        # Écriture 4 : Montant encaissé net
        lignes.append({
            "STE": "DLM",
            "DATE": date_ecriture,
            "COMPTE": "512120",
            "Auxiliaire": "",
            "n°pièce": objet,
            "OBJET": objet,
            "D": f"{difference:.2f}".replace(".", ","),
            "C": "",
            "Journal": "CEBOOBA",
            "Analytique": ""
        })

    # Aucun mouvement détecté → fichier non conforme
    if not lignes:
        raise NotAlmaFileError("Aucune ligne ALMA détectée")

    # Génération du fichier comptable final
    df_final = pd.DataFrame(lignes)
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_alma.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")
