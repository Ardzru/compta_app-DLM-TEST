# handlers/compta_handler.py

import pandas as pd
from pathlib import Path

JOURNAUX_VE     = ["VE"]
JOURNAUX_ARGENT = ["AC", "CEBOOBA"]

PRO_PARTENAIRES = {
    1461: "OT THONON LES BAINS", 1462: "MOUNTAIN XTRA",
    1463: "My home in the alps", 1464: "45 DEGREES NORTH LTD",
    1465: "AIGLON", 1466: "ALIKATS",
    1467: "ALPEN ROC", 1468: "ALPINE ACTIVE (JACK AND JILL)",
    1469: "ALPINE GENERATION", 1470: "ALPTITUDE",
    1471: "ALTE NEVE", 1472: "ECOLE DE SKI MORZINE-AVORIAZ",
    1489: "SEASONAL BEDS", 1490: "BAUD AGENCE",
    1495: "CHALET FOURMILIERE", 1510: "FLEUR DES NEIGES",
    1520: "GRAND TETRAS", 1529: "MOUNTAIN SPACES",
    1539: "DAHU", 1540: "MOUNTAIN HIGHS",
    1548: "EQUIPE", 1561: "FARMHOUSE",
    1575: "IMPACT ALPS", 1580: "IGOSKI",
    1590: "LACOUTETE", 1597: "SPORTING",
    1600: "TREMPLIN", 1602: "BERGERIE",
    1617: "MORZINE SKI CHALETS", 1624: "PETIT DRU",
    1637: "SAMOYEDE", 1651: "TUI",
    1684: "MORZINE RESERVATION", 1727: "LA CLEF DES CHAMPS",
    1734: "CHAMPS FLEURIS", 1738: "COTES",
    1743: "CRET", 1754: "MORZINE IMMOBILIER",
    1764: "HOTELPLAN LTD", 1781: "VITA BREVIS LTD",
    1787: "MILEADE", 1793: "PURE MORZINE",
    1802: "REACH4THEALPS", 1808: "SIMPLY MORZINE SARL",
    1820: "MORE MOUNTAIN", 1829: "VILLAGES CLUBS DU SOLEIL",
    1838: "MOUNTAIN XTRA", 1841: "BRAVEHEART",
    1860: "HOTEL MONTRIOND", 1869: "MOUNTAIN HEAVEN",
    1877: "MOUNTAIN MAVERICKS", 1886: "SUMMIT TRAVEL",
    1890: "WETRIP LTD", 1898: "EMERALD STAY",
    2091: "BOUTIQUE CHALET", 2092: "HOFNAR",
    2093: "HUNTER CHALET", 2094: "MOUNTAIN MOMENTS",
    2095: "NUCO TRAVEL", 2096: "RIDERS REFUGE",
    2097: "SKI ELEMENT LTD", 2098: "SKI ZOOM LTD",
    2099: "SKIOLOGY", 2101: "TG SKI",
    2102: "TREELINE", 2103: "WASTELAND TRAVEL",
    2198: "HOTEL CHAUMIERE", 2199: "HOST SAVOIE",
    2200: "ARTES TOURISME", 2201: "SAVOY ET NANT",
    2202: "SNOW BROKER", 2203: "TRIP&CO",
    2204: "VERY MOUNTAIN", 2205: "ELEVATION ALPS CONCIERGE",
    2214: "Frajopi", 2222: "Snow Candy",
    2245: "La Banquise", 2294: "CONCORDE",
}


def _get_engine(fichier: Path) -> str:
    return "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"


def est_compta(fichier: Path) -> bool:
    """Détecte un fichier compta via la colonne 'Libellé écriture'"""
    try:
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, engine=engine, nrows=5)
        return "Libellé écriture" in df.columns
    except:
        return False


def charger_compta(fichier: Path) -> pd.DataFrame:
    """
    Charge le fichier compta et retourne un DataFrame normalisé :
    - num_commande  : str (colonne 'Libellé écriture')
    - montant_signe : float
    - journal       : str
    - debit         : float
    - credit        : float
    - type_ecriture : 'VE' | 'ARGENT_RECU' | 'AUTRE'
    - est_pro       : bool
    - nom_partenaire: str ou None
    - date          : date
    """
    try:
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, engine=engine, dtype=str)

        # Nettoyage colonnes
        df.columns = [c.strip() for c in df.columns]

        resultat = pd.DataFrame()

        resultat["date"]          = pd.to_datetime(df.get("Date", pd.Series()), errors="coerce")
        resultat["montant_signe"] = pd.to_numeric(df.get("Montant signé", pd.Series()), errors="coerce")
        resultat["journal"]       = df.get("Journal", pd.Series()).astype(str).str.strip().str.upper()
        resultat["num_commande"]  = df.get("Libellé écriture", pd.Series()).astype(str).str.strip()
        resultat["debit"]         = pd.to_numeric(df.get("Débit", pd.Series()), errors="coerce")
        resultat["credit"]        = pd.to_numeric(df.get("Crédit", pd.Series()), errors="coerce")
        resultat["num_piece"]     = df.get("N° pièce", pd.Series()).astype(str).str.strip()

        # Colonne A = première colonne brute (numéro portail pour les PRO)
        col_a = df.iloc[:, 0].astype(str).str.strip()

        # Type d'écriture
        def type_ecriture(j):
            if j in JOURNAUX_VE:
                return "VE"
            elif j in JOURNAUX_ARGENT:
                return "ARGENT_RECU"
            return "AUTRE"

        resultat["type_ecriture"] = resultat["journal"].apply(type_ecriture)

        # Détection PRO
        def get_pro(val):
            try:
                num = int(float(val))
                return PRO_PARTENAIRES.get(num, None)
            except:
                return None

        resultat["nom_partenaire"] = col_a.apply(get_pro)
        resultat["est_pro"]        = resultat["nom_partenaire"].notna()

        # Garder uniquement les num_commande à 8 chiffres
        resultat = resultat[resultat["num_commande"].str.match(r"^\d{8}$")]
        resultat = resultat.dropna(subset=["montant_signe"])

        return resultat

    except Exception as e:
        print(f"[ComptaHandler] Erreur sur {fichier.name} : {e}")
        return pd.DataFrame()


def traiter_compta(fichier: Path) -> None:
    """Point d'entrée appelé par le dispatcher."""
    df = charger_compta(fichier)

    if df.empty:
        print(f"[ComptaHandler] Aucune donnée exploitable dans {fichier.name}")
        return

    nb_ve     = (df["type_ecriture"] == "VE").sum()
    nb_argent = (df["type_ecriture"] == "ARGENT_RECU").sum()
    nb_pro    = df["est_pro"].sum()

    print(f"[ComptaHandler] {len(df)} lignes — VE: {nb_ve} | Argent reçu: {nb_argent} | PRO: {nb_pro}")
    # TODO : rapprochement avec banque / alpilink
