# handlers/alpilink_handler.py

import pandas as pd
from pathlib import Path

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

STATUTS_VALIDES = ["Payée banque", "Attente retour client"]


def _get_engine(fichier: Path) -> str:
    return "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"


def est_alpilink(fichier: Path) -> bool:
    """Détecte un fichier Alpilink : nom commence par 'data'"""
    return fichier.stem.lower().startswith("data")


def charger_alpilink(fichier: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Retourne deux DataFrames :
    1. df_normal  : commandes Alpilink classiques agrégées par num_commande
    2. df_buyclub : commandes BuyClub (présence = OK)

    Colonnes df_normal  : num_commande | montant_total | statut | est_pro | nom_partenaire
    Colonnes df_buyclub : num_commande
    """
    try:
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, header=0, engine=engine, dtype=str)

        cols = df.columns.tolist()

        def col(lettre):
            idx = ord(lettre.upper()) - ord('A')
            return df.iloc[:, idx] if idx < len(cols) else pd.Series(dtype=str)

        col_a = col("A").astype(str).str.strip()
        col_c = col("C").astype(str).str.strip()
        col_r = col("R").astype(str).str.strip()
        col_s = col("S").astype(str).str.strip()
        col_y = col("Y").astype(str).str.strip()
        col_z = pd.to_numeric(col("Z"), errors="coerce")

        df_work = pd.DataFrame({
            "col_a": col_a,
            "col_c": col_c,
            "col_r": col_r,
            "col_s": col_s,
            "col_y": col_y,
            "montant": col_z,
        })

        # Séparer BuyClub
        mask_buyclub = df_work["col_c"].str.upper().str.contains("SC9972:BUY", na=False)
        df_buyclub = df_work[mask_buyclub][["col_r"]].rename(columns={"col_r": "num_commande"})
        df_buyclub = df_buyclub.dropna(subset=["num_commande"])

        # Alpilink classique — filtrer statuts valides
        df_normal = df_work[~mask_buyclub].copy()
        df_normal = df_normal[df_normal["col_y"].isin(STATUTS_VALIDES)]

        # Numéro de commande : S si S != "0", sinon R
        df_normal["num_commande"] = df_normal.apply(
            lambda row: row["col_s"] if row["col_s"] != "0" else row["col_r"],
            axis=1
        )
        df_normal = df_normal.dropna(subset=["num_commande", "montant"])

        # Agréger montants par numéro de commande
        df_agg = (
            df_normal.groupby("num_commande")
            .agg(
                montant_total=("montant", "sum"),
                statut=("col_y", "first"),
                col_a=("col_a", "first"),
            )
            .reset_index()
        )

        # Détecter commandes PRO via colonne A
        def get_pro(val):
            try:
                num = int(float(val))
                return PRO_PARTENAIRES.get(num, None)
            except:
                return None

        df_agg["nom_partenaire"] = df_agg["col_a"].apply(get_pro)
        df_agg["est_pro"] = df_agg["nom_partenaire"].notna()
        df_agg = df_agg.drop(columns=["col_a"])

        return df_agg, df_buyclub

    except Exception as e:
        print(f"[AlpilinkHandler] Erreur sur {fichier.name} : {e}")
        return pd.DataFrame(), pd.DataFrame()


def traiter_alpilink(fichier: Path) -> None:
    """Point d'entrée appelé par le dispatcher."""
    df_normal, df_buyclub = charger_alpilink(fichier)

    if df_normal.empty and df_buyclub.empty:
        print(f"[AlpilinkHandler] Aucune donnée exploitable dans {fichier.name}")
        return

    print(f"[AlpilinkHandler] {len(df_normal)} commandes classiques, {len(df_buyclub)} BuyClub")
    # TODO : rapprochement avec compta
