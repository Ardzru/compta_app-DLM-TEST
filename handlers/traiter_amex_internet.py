import pandas as pd
from pathlib import Path
from config import DOSSIER_SORTIE


def nettoyer_montant(val):
    """
    Nettoie et convertit un montant AMEX :
    - Gère les valeurs vides
    - Supprime les séparateurs de milliers
    - Gère les montants négatifs suffixés par '-'
    - Retourne 0.0 en cas d’erreur
    """
    if pd.isna(val):
        return 0.0

    s = str(val).strip()
    s = s.replace(".", "").replace(",", ".")

    # Cas AMEX : montant négatif avec '-' en suffixe
    if s.endswith("-"):
        s = "-" + s[:-1]

    try:
        return float(s)
    except ValueError:
        return 0.0


def formater_date(val):
    """
    Formate une date au format JJ/MM/AAAA.
    Le fichier AMEX utilise un format jour en premier.
    """
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        return None
    return d.strftime("%d/%m/%Y")


def traiter_amex_internet(fichier: Path):
    """
    Traite un fichier AMEX Internet et génère les écritures comptables.

    Règles métier principales :
    - Seules les lignes contenant 'SITE' sont traitées
    - Trois cas gérés :
        1. Remboursement client
        2. Encaissement simple
        3. Encaissement avec frais
    """

    # Choix du moteur Excel selon le format
    engine = "xlrd" if fichier.suffix.lower() == ".xls" else "openpyxl"
    df = pd.read_excel(fichier, header=None, engine=engine)

    # Index des colonnes AMEX (format fournisseur)
    COL_DATE_LIB = 0       # Date affichée (libellé)
    COL_DATE_COMPTA = 13   # Date comptable
    COL_D = 3              # Montant brut
    COL_E = 4              # Montant crédité / débité
    COL_G = 6              # Frais AMEX
    COL_I = 8              # Montant net
    COL_SIGNATURE = 14     # Signature (SITE / CAISSE)

    lignes = []

    # Parcours ligne par ligne du fichier AMEX
    for _, row in df.iterrows():

        # Filtrage AMEX Internet uniquement
        signature = str(row[COL_SIGNATURE]).strip().upper()
        if "SITE" not in signature:
            continue

        # Dates
        date_lib = formater_date(row[COL_DATE_LIB])
        date_compta = formater_date(row[COL_DATE_COMPTA])
        if not date_lib or not date_compta:
            continue

        # Montants
        D = nettoyer_montant(row[COL_D])
        E = nettoyer_montant(row[COL_E])
        G = nettoyer_montant(row[COL_G])
        I = nettoyer_montant(row[COL_I])

        # Ligne vide ou non exploitable
        if D == 0 and E == 0 and G == 0 and I == 0:
            continue

        piece = f"AMEX INTERNET DU {date_lib}"

        # ------------------------------------------------------------
        # CAS 1 — REMBOURSEMENT CLIENT
        # E négatif, pas de frais
        # ------------------------------------------------------------
        if E < 0 and G == 0:
            montant = abs(E)

            lignes.extend([
                {
                    "STE": "DLM",
                    "DATE": date_compta,
                    "COMPTE": "512120",
                    "Auxiliaire": "",
                    "n°pièce": piece,
                    "OBJET": piece,
                    "D": "",
                    "C": f"{montant:.2f}".replace(".", ","),
                    "Journal": "CEBOOBA",
                    "Analytique": ""
                },
                {
                    "STE": "DLM",
                    "DATE": date_compta,
                    "COMPTE": "580010DS5",
                    "Auxiliaire": "",
                    "n°pièce": piece,
                    "OBJET": piece,
                    "D": f"{montant:.2f}".replace(".", ","),
                    "C": "",
                    "Journal": "CEBOOBA",
                    "Analytique": ""
                }
            ])
            continue

        # ------------------------------------------------------------
        # CAS 2 — ENCAISSEMENT SIMPLE (sans frais)
        # ------------------------------------------------------------
        if E > 0:
            lignes.extend([
                {
                    "STE": "DLM",
                    "DATE": date_compta,
                    "COMPTE": "512120",
                    "Auxiliaire": "",
                    "n°pièce": piece,
                    "OBJET": piece,
                    "D": "",
                    "C": f"{E:.2f}".replace(".", ","),
                    "Journal": "CEBOOBA",
                    "Analytique": ""
                },
                {
                    "STE": "DLM",
                    "DATE": date_compta,
                    "COMPTE": "580010DS5",
                    "Auxiliaire": "",
                    "n°pièce": piece,
                    "OBJET": piece,
                    "D": f"{I:.2f}".replace(".", ","),
                    "C": "",
                    "Journal": "CEBOOBA",
                    "Analytique": ""
                }
            ])
            continue

        # ------------------------------------------------------------
        # CAS 3 — ENCAISSEMENT AVEC FRAIS AMEX
        # ------------------------------------------------------------
        lignes.extend([
            {
                "STE": "DLM",
                "DATE": date_compta,
                "COMPTE": "580010DS5",
                "Auxiliaire": "",
                "n°pièce": piece,
                "OBJET": piece,
                "D": "",
                "C": f"{D:.2f}".replace(".", ","),
                "Journal": "CEBOOBA",
                "Analytique": ""
            },
            {
                "STE": "DLM",
                "DATE": date_compta,
                "COMPTE": "627800",
                "Auxiliaire": "",
                "n°pièce": piece,
                "OBJET": piece,
                "D": f"{abs(G):.2f}".replace(".", ","),
                "C": "",
                "Journal": "CEBOOBA",
                "Analytique": "ST-CT00-XX"
            },
            {
                "STE": "DLM",
                "DATE": date_compta,
                "COMPTE": "512120",
                "Auxiliaire": "",
                "n°pièce": piece,
                "OBJET": piece,
                "D": f"{I:.2f}".replace(".", ","),
                "C": "",
                "Journal": "CEBOOBA",
                "Analytique": ""
            }
        ])

    # ------------------------------------------------------------
    # EXPORT DU FICHIER COMPTABLE
    # ------------------------------------------------------------
    if lignes:
        df_final = pd.DataFrame(lignes)
        sortie = DOSSIER_SORTIE / f"{fichier.name}_amex_internet.csv"
        df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")
