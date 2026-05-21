# handlers/banque_handler.py

import pandas as pd
from pathlib import Path

CONTRATS = {
    "7770571305": "AMEX",
    "831103222":  "PLANET",
    "8430996":    "CB",
}

def _get_engine(fichier: Path) -> str:
    return "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"

def est_banque(fichier: Path) -> bool:
    """Détecte un fichier banque via le numéro de contrat en colonne B"""
    try:
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, header=None, engine=engine, dtype=str)
        col_b = df[1].astype(str).str.strip()
        return col_b.isin(CONTRATS.keys()).any()
    except:
        return False

def charger_banque(fichier: Path) -> pd.DataFrame:
    """
    Charge un fichier banque et retourne un DataFrame normalisé :
    - num_commande : 8 chiffres (colonne C, sans le M initial)
    - type_flux    : 'Débit' ou 'Crédit' (colonne E)
    - montant      : float (colonne G)
    - source       : 'AMEX', 'PLANET' ou 'CB'
    """
    try:
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, header=None, engine=engine, dtype=str)

        # Identifier la source via colonne B
        col_b = df[1].astype(str).str.strip()
        source = "INCONNU"
        for num, nom in CONTRATS.items():
            if col_b.isin([num]).any():
                source = nom
                break

        # Colonnes : C=2, E=4, G=6
        resultat = pd.DataFrame()
        resultat["num_commande"] = (
            df[2].astype(str).str.strip()
            .str.replace(r"^M", "", regex=True)   # enlève le M initial
            .str.extract(r"(\d{8})")[0]            # garde uniquement 8 chiffres
        )
        resultat["type_flux"] = df[4].astype(str).str.strip()  # Débit / Crédit
        resultat["montant"]   = pd.to_numeric(df[6], errors="coerce")
        resultat["source"]    = source
        resultat["fichier"]   = fichier.name

        # Ne garder que les lignes avec un numéro de commande valide
        resultat = resultat.dropna(subset=["num_commande", "montant"])
        resultat = resultat[resultat["num_commande"].str.match(r"^\d{8}$")]

        return resultat

    except Exception as e:
        print(f"[BanqueHandler] Erreur sur {fichier.name} : {e}")
        return pd.DataFrame()


def traiter_banque(fichier: Path) -> None:
    """Point d'entrée appelé par le dispatcher."""
    df = charger_banque(fichier)

    if df.empty:
        print(f"[BanqueHandler] Aucune donnée exploitable dans {fichier.name}")
        return

    print(f"[BanqueHandler] {len(df)} lignes chargées depuis {fichier.name} (source: {df['source'].iloc[0]})")
    # TODO : rapprochement avec compta
