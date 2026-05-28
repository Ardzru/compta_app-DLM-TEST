# core/utils/constantes.py
"""
Constantes comptables centralisées - utilisées par tous les handlers
"""

# ==========================================================
# COMPTES COMPTABLES
# ==========================================================
COMPTE_TRANSIT = "580010DS5"
COMPTE_AVOIR = "580012DS5"
COMPTE_BANQUE = "512120"
COMPTE_FOURN = "401000"

# Aliases pour clarté métier
COMPTE_VENTE = COMPTE_TRANSIT  # Pour PLANET
COMPTE_COMM = COMPTE_FOURN     # Pour PLANET (frais)
COMPTE_PRINCIPAL = COMPTE_BANQUE  # Pour PLANET
COMPTE_COMMANDE = COMPTE_TRANSIT  # Pour AVOIRS
COMPTE_TVA = "44571"  # Pour KIOSK_PHOTO
COMPTE_PRODUITS = "706"  # Pour KIOSK_PHOTO

# ==========================================================
# AUXILIAIRES
# ==========================================================
AUX_FOURN_ALMA = "ALMA"
AUX_PLANET = "PLANET MERCHANT SERVICES"

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
# JOURNAUX
# ==========================================================
JOURNAUX = {
    "alma": "VE",
    "amex_caisse": "CA",
    "amex_internet": "CB",
    "ancv": "VE",
    "avoirs": "VE",
    "banque": "BQ",
    "ta": "CA",
    "kiosk_photo": "VE",
    "planet": "BQ",
}

# ==========================================================
# COLONNES FICHIERS SOURCES
# ==========================================================

# AMEX CAISSE
AMEX_CAISSE_COL = {
    "date_reglement": 1,
    "date_transaction": 14,
    "type": 4,
    "num_ref": 3,
    "num_reglement": 2,
    "montant_brut": 20,
    "frais": 23,
    "montant_net": 26,
    "roc_id_terminal": 7,
}

# PLANET
PLANET_COL = {
    "type": 6,
    "lot": 11,
    "brut": 13,
    "date_txn": 15,
    "date_val": 30,
    "comm": 23,
    "libel": 31,
    "tva": 39,
}

__all__ = [
    # Comptes
    "COMPTE_TRANSIT",
    "COMPTE_AVOIR",
    "COMPTE_BANQUE",
    "COMPTE_FOURN",
    "COMPTE_VENTE",
    "COMPTE_COMM",
    "COMPTE_PRINCIPAL",
    "COMPTE_COMMANDE",
    "COMPTE_TVA",
    "COMPTE_PRODUITS",
    # Auxiliaires
    "AUX_FOURN_ALMA",
    "AUX_PLANET",
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
    # Métier
    "JOURNAUX",
    "AMEX_CAISSE_COL",
    "PLANET_COL",
]
