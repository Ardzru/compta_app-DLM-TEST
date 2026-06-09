"""
Constantes comptables centralisées - utilisées par tous les modules
"""

# ==========================================================
# SOCIÉTÉ
# ==========================================================
STE_DLM = "DLM"

# ==========================================================
# JOURNAUX
# ==========================================================
JOURNAL_AC = "AC"
JOURNAL_OD = "OD"
JOURNAL_VE = "VE"
JOURNAL_CEBOOBA = "CEBOOBA"
JOURNAL_CAA = "CAA"

JOURNAUX = {
    "alma": JOURNAL_VE,
    "amex_caisse": JOURNAL_CAA,
    "amex_internet": JOURNAL_CEBOOBA,
    "ancv": JOURNAL_VE,
    "avoirs": JOURNAL_OD,
    "banque": JOURNAL_CEBOOBA,
    "ta": JOURNAL_VE,
    "kiosk_photo": JOURNAL_VE,
    "planet": JOURNAL_CEBOOBA,
}

JOURNAUX_VE = ["VE"]
JOURNAUX_ARGENT = ["AC", "CEBOOBA"]

# ==========================================================
# ANALYTIQUES
# ==========================================================
ANALYTIQUE_VIDE = ""
ANALYTIQUE_FRAIS_CB = "AD-CO00-XX"
ANALYTIQUE_FRAIS = "AD-CO00-XX"
ANALYTIQUE_FRAIS_AMEX = "AD-CO00-XX"

# ==========================================================
# AUXILIAIRES
# ==========================================================
AUXILIAIRE_VIDE = ""
AUXILIAIRE_ALMA = "ALMA"
AUX_FOURN_ALMA = "ALMA"
AUX_PLANET = "PLANET MERCHANT SERVICES"

# ==========================================================
# COMPTES — ALMA
# ==========================================================
COMPTE_TRANSIT_ALMA = "580010DS5"
COMPTE_BANQUE_ALMA = "512120"
COMPTE_FOURN_ALMA = "401000"

# ==========================================================
# COMPTES — AMEX CAISSE
# ==========================================================
COMPTE_BANQUE_AMEX_CAISSE = "512121"
COMPTE_AMEX_CAISSE_TRANSIT = "580011"
COMPTE_FRAIS_CB = "627800"

# ==========================================================
# COMPTES — AMEX INTERNET
# ==========================================================
COMPTE_TRANSIT_AMEX_INTERNET = "580010DS5"
COMPTE_BANQUE_AMEX_INTERNET = "512120"
COMPTE_FRAIS_AMEX = "627800"
COMPTE_FRAIS_AMEX_INTERNET = "627800"

# ==========================================================
# COMPTES — ANCV
# ==========================================================
COMPTE_ANCV_CAISSE = "580004"

# ==========================================================
# COMPTES — KIOSK PHOTO
# ==========================================================
COMPTE_VENTES = "706000"
COMPTE_TVA_COLLECTEE = "445710"
COMPTE_MONNAYEUR = "580001"
COMPTE_TPE = "580005"

# ==========================================================
# COMPTES — PLANET
# ==========================================================
COMPTE_TRANSIT_PLANET_CAISSE   = "580005"
COMPTE_TRANSIT_PLANET_INTERNET = "580010DS5"


# ==========================================================
# COMPTES — GÉNÉRIQUES
# ==========================================================
COMPTE_TRANSIT = "580010DS5"
COMPTE_AVOIR = "580012DS5"
COMPTE_BANQUE = "512120"
COMPTE_FOURN = "401000"
COMPTE_CLIENT = "411000"
COMPTE_VENTE = "707000"
COMPTE_COMM = "401000"
COMPTE_PRINCIPAL = "512120"
COMPTE_TPE_CARTE = "5121"
COMPTE_CAISSE = "5301"
COMPTE_TVA = "44571"
COMPTE_PRODUITS = "706"

# ==========================================================
# COLONNES DE SORTIE (COMPTA)
# ==========================================================
COL_STE = "STE"
COL_DATE = "DATE"
COL_COMPTE = "COMPTE"
COL_AUX = "Auxiliaire"
COL_PIECE = "n°pièce"
COL_OBJET = "OBJET"
COL_DEBIT = "D"
COL_CREDIT = "C"
COL_JOURNAL = "Journal"
COL_ANALYTIQUE = "Analytique"

COLONNES_SORTIE = [
    COL_STE,
    COL_DATE,
    COL_COMPTE,
    COL_AUX,
    COL_PIECE,
    COL_OBJET,
    COL_DEBIT,
    COL_CREDIT,
    COL_JOURNAL,
    COL_ANALYTIQUE,
]

# ==========================================================
# COLONNES AMEX CAISSE (Module 1)
# ==========================================================
AMEX_CAISSE_COL = {
    "date": 0,
    "montant": 1,
    "tva": 2,
    "frais": 3,
    "reference": 4,
    "libelle": 5,
}

# ==========================================================
# COLONNES PLANET (Module 1)
# ==========================================================
PLANET_COL = {
    "type": 6,
    "lot": 11,
    "brut": 13,
    "date_txn": 15,
    "date_val_internet": 30,
    "date_val_caisses": 29,
    "comm": 23,
    "libel": 31,
    "tva": 39,
}

# ==========================================================
# TA (Team Axess)
# ==========================================================
TA_COL = {
    "date": "DATE",
    "commande": "VALEUR PROMPT",
    "caisse": "CAISSE",
    "montant": "MONTANT",
    "libelle": "SZNAME",
}

TA_CAISSES_AUTORISEES = {"72", "73", "77"}

TA_LIBELLES_VENTES = {
    "Vente d'un titre",
    "Vente d'un article",
    "Prêt",
}

TA_LIBELLES_ANNULATIONS = {
    "Annulation automatique",
    "Annulation article",
}

# ==========================================================
# CONSTANTES BANQUE
# ==========================================================
CONTRATS_BANQUE = {
    "7770571305": "AMEX",
    "831103222": "PLANET",
    "8430996": "CB",
}

COLONNES_BANQUE = ["Date", "Libellé", "Débit", "Crédit", "Montant", "N° Pièce"]

# ==========================================================
# PARTENAIRES & STATUTS
# ==========================================================

PRO_PARTENAIRES = {
    1461: "OT THONON LES BAINS",
    1462: "MOUNTAIN XTRA",
    1463: "My home in the alps",
    1464: "45 DEGREES NORTH LTD",
    1465: "AIGLON",
    1466: "ALIKATS",
    1467: "ALPEN ROC",
    1468: "ALPINE ACTIVE (JACK AND JILL)",
    1469: "ALPINE GENERATION",
    1470: "ALPTITUDE",
    1471: "ALTE NEVE",
    1472: "ECOLE DE SKI MORZINE-AVORIAZ",
    1489: "SEASONAL BEDS",
    1490: "BAUD AGENCE",
    1495: "CHALET FOURMILIERE",
    1510: "FLEUR DES NEIGES",
    1520: "GRAND TETRAS",
    1529: "MOUNTAIN SPACES",
    1539: "DAHU",
    1540: "MOUNTAIN HIGHS",
    1548: "EQUIPE",
    1561: "FARMHOUSE",
    1575: "IMPACT ALPS",
    1580: "IGOSKI",
    1590: "LACOUTETE",
    1597: "SPORTING",
    1600: "TREMPLIN",
    1602: "BERGERIE",
    1617: "MORZINE SKI CHALETS",
    1624: "PETIT DRU",
    1637: "SAMOYEDE",
    1651: "TUI",
    1684: "MORZINE RESERVATION",
    1727: "LA CLEF DES CHAMPS",
    1734: "CHAMPS FLEURIS",
    1738: "COTES",
    1743: "CRET",
    1754: "MORZINE IMMOBILIER",
    1764: "HOTELPLAN LTD",
    1781: "VITA BREVIS LTD",
    1787: "MILEADE",
    1793: "PURE MORZINE",
    1802: "REACH4THEALPS",
    1808: "SIMPLY MORZINE SARL",
    1820: "MORE MOUNTAIN",
    1829: "VILLAGES CLUBS DU SOLEIL",
    1838: "MOUNTAIN XTRA",
    1841: "BRAVEHEART",
    1860: "HOTEL MONTRIOND",
    1869: "MOUNTAIN HEAVEN",
    1877: "MOUNTAIN MAVERICKS",
    1886: "SUMMIT TRAVEL",
    1890: "WETRIP LTD",
    1898: "EMERALD STAY",
    2091: "BOUTIQUE CHALET",
    2092: "HOFNAR",
    2093: "HUNTER CHALET",
    2094: "MOUNTAIN MOMENTS",
    2095: "NUCO TRAVEL",
    2096: "RIDERS REF",
}

ALPILINK_STATUTS_VALIDES = ["Payée banque", "Attente retour client"]

# ==========================================================
# EXPORT
# ==========================================================
__all__ = [
    # Société
    "STE_DLM",

    # Journaux
    "JOURNAL_AC",
    "JOURNAL_OD",
    "JOURNAL_VE",
    "JOURNAL_CEBOOBA",
    "JOURNAL_CAA",
    "JOURNAUX",
    "JOURNAUX_VE",
    "JOURNAUX_ARGENT",

    # Analytiques
    "ANALYTIQUE_VIDE",
    "ANALYTIQUE_FRAIS_CB",
    "ANALYTIQUE_FRAIS",
    "ANALYTIQUE_FRAIS_AMEX",

    # Auxiliaires
    "AUXILIAIRE_VIDE",
    "AUXILIAIRE_ALMA",
    "AUX_FOURN_ALMA",
    "AUX_PLANET",

    # Comptes ALMA
    "COMPTE_TRANSIT_ALMA",
    "COMPTE_BANQUE_ALMA",
    "COMPTE_FOURN_ALMA",

    # Comptes AMEX CAISSE
    "COMPTE_BANQUE_AMEX_CAISSE",
    "COMPTE_AMEX_CAISSE_TRANSIT",
    "COMPTE_FRAIS_CB",

    # Comptes AMEX INTERNET
    "COMPTE_TRANSIT_AMEX_INTERNET",
    "COMPTE_BANQUE_AMEX_INTERNET",
    "COMPTE_FRAIS_AMEX",
    "COMPTE_FRAIS_AMEX_INTERNET",

    # Comptes ANCV
    "COMPTE_ANCV_CAISSE",

    # Comptes KIOSK PHOTO
    "COMPTE_VENTES",
    "COMPTE_TVA_COLLECTEE",
    "COMPTE_MONNAYEUR",
    "COMPTE_TPE",

    # Comptes PLANET
    "COMPTE_TRANSIT_PLANET_CAISSE",
    "COMPTE_TRANSIT_PLANET_INTERNET",


    # Comptes génériques
    "COMPTE_TRANSIT",
    "COMPTE_AVOIR",
    "COMPTE_BANQUE",
    "COMPTE_FOURN",
    "COMPTE_CLIENT",
    "COMPTE_VENTE",
    "COMPTE_COMM",
    "COMPTE_PRINCIPAL",
    "COMPTE_TPE_CARTE",
    "COMPTE_CAISSE",
    "COMPTE_TVA",
    "COMPTE_PRODUITS",

    # Colonnes
    "COL_STE",
    "COL_DATE",
    "COL_COMPTE",
    "COL_AUX",
    "COL_PIECE",
    "COL_OBJET",
    "COL_DEBIT",
    "COL_CREDIT",
    "COL_JOURNAL",
    "COL_ANALYTIQUE",
    "COLONNES_SORTIE",

    # Colonnes spécialisées
    "AMEX_CAISSE_COL",
    "PLANET_COL",
    "TA_COL",
    "TA_CAISSES_AUTORISEES",
    "TA_LIBELLES_VENTES",
    "TA_LIBELLES_ANNULATIONS",

    # Partenaires
    "PRO_PARTENAIRES",
    "ALPILINK_STATUTS_VALIDES",
    "CONTRATS_BANQUE",
    "COLONNES_BANQUE",
]
