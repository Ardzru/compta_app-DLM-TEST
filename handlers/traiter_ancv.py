import pandas as pd
from pathlib import Path
from config import DOSSIER_SORTIE


def nettoyer_montant(val):
    """
    Nettoie et convertit un montant ANCV :
    - Remplace la virgule par un point
    - Supprime les espaces
    - Convertit en float
    - Retourne 0.0 en cas d’erreur
    """
    try:
        return float(str(val).replace(",", ".").strip())
    except Exception:
        return 0.0


def formater_date(val):
    """
    Formate une date au format JJ/MM/AAAA.
    Le fichier ANCV utilise un format jour en premier.
    """
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        return None
    return d.strftime("%d/%m/%Y")


def traiter_ancv(fichier: Path):
    """
    Traite un fichier ANCV Connect et génère les écritures comptables.

    Règles métier principales :
    - Seules les transactions VALIDATED et FINALISÉES sont prises en compte
    - Le montant doit être strictement positif
    - Le compte dépend de la longueur de la référence (Internet / Caisse)
    """

    # Lecture du fichier CSV ANCV
    df = pd.read_csv(fichier, sep=";", dtype=str)

    # Fichier vide → rien à traiter
    if df.empty:
        return

    # ------------------------------------------------------------
    # NORMALISATION DES DONNÉES
    # ------------------------------------------------------------

    # Nettoyage des noms de colonnes
    df.columns = [c.strip() for c in df.columns]

    # Normalisation des champs texte utilisés pour le filtrage
    df["EtatANCV"] = df["EtatANCV"].astype(str).str.strip().str.upper()
    df["Transaction Finalisée"] = (
        df["Transaction Finalisée"].astype(str).str.strip().str.upper()
    )

    # Nettoyage du montant AVANT filtrage (point clé)
    df["CVCo"] = df["CVCo"].apply(nettoyer_montant)

    # ------------------------------------------------------------
    # FILTRAGE MÉTIER
    # ------------------------------------------------------------

    df = df[
        (df["EtatANCV"] == "VALIDATED") &
        (df["Transaction Finalisée"] == "TRUE") &
        (df["CVCo"] > 0)
    ].copy()

    # Aucun mouvement exploitable
    if df.empty:
        return

    lignes = []
    totaux = {}

    # ------------------------------------------------------------
    # LIGNES DÉTAILLÉES (CRÉDIT)
    # ------------------------------------------------------------

    for _, row in df.iterrows():

        # Date de création de la transaction
        date = formater_date(row["Date de création(UTC)"])
        if not date:
            continue

        # Référence de commande
        reference = str(row["Order Id"]).strip()
        if not reference:
            continue

        montant = row["CVCo"]

        # Règle métier :
        # - 8 caractères → ANCV Internet
        # - sinon → ANCV Caisse
        compte = "580010DS5" if len(reference) == 8 else "580004"

        piece = (
            f"ANCV connect Internet du {date}"
            if compte == "580010DS5"
            else f"ANCV connect Caisse du {date}"
        )

        # Écriture détaillée (crédit)
        lignes.append({
            "STE": "DLM",
            "DATE": date,
            "COMPTE": compte,
            "Auxiliaire": "",
            "n°pièce": piece,
            "OBJET": reference,
            "D": "",
            "C": f"{montant:.2f}".replace(".", ","),
            "Journal": "CEBOOBA",
            "Analytique": ""
        })

        # Cumul pour la contrepartie
        totaux[(date, compte)] = totaux.get((date, compte), 0) + montant

    # ------------------------------------------------------------
    # CONTREPARTIES REGROUPÉES (DÉBIT)
    # ------------------------------------------------------------

    for (date, compte), total in totaux.items():

        piece = (
            f"ANCV connect Internet du {date}"
            if compte == "580010DS5"
            else f"ANCV connect Caisse du {date}"
        )

        lignes.append({
            "STE": "DLM",
            "DATE": date,
            "COMPTE": compte,
            "Auxiliaire": "",
            "n°pièce": piece,
            "OBJET": piece,
            "D": f"{total:.2f}".replace(".", ","),
            "C": "",
            "Journal": "CEBOOBA",
            "Analytique": ""
        })

    if not lignes:
        return

    # ------------------------------------------------------------
    # EXPORT DU FICHIER COMPTABLE
    # ------------------------------------------------------------

    df_final = pd.DataFrame(lignes)

    sortie = DOSSIER_SORTIE / f"{fichier.stem}_ancv.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")
