"""
Constantes centralisées pour les noms de colonnes et configurations.
"""
import pandas as pd

# ============================================================================
# COLONNES COMPTABLES STANDARD
# ============================================================================
COL_COMPTA_DATE     = "Date"
COL_COMPTA_CREDIT   = "Crédit"
COL_COMPTA_DEBIT    = "Débit"
COL_COMPTA_MONTANT  = "Montant signé"
COL_COMPTA_LIBELLE  = "Libellé écriture"
COL_COMPTA_JOURNAL  = "Journal"
COL_COMPTA_SENS     = "Sens"
COL_COMPTA_LETTRAGE = "Lettrage"
COL_COMPTA_PIECE    = "Libellé écriture"

# ============================================================================
# COLONNES BANQUE
# ============================================================================
COL_BANQUE_DATE        = "Date du paiement"
COL_BANQUE_COMMAND     = "Commande"
COL_BANQUE_MONTANT     = "Montant du paiement"
COL_BANQUE_TYPE        = "Moyen de paiement"
COL_BANQUE_EMAIL       = "E-mail acheteur"
COL_BANQUE_STATUT      = "Statut rapprochement"
COL_BANQUE_CONTRAT     = "Contrat commerçant"
COL_BANQUE_REMISE      = "N° remise"
COL_BANQUE_DATE_REMISE = "Date remise"

# ============================================================================
# COLONNES ALPILINK
# ============================================================================
COL_ALPI_ID_CMD     = "Id Commande"
COL_ALPI_MONTANT    = "Prix Total"
COL_ALPI_STATUT     = "Statut"
COL_ALPI_CANAL      = "Canal de vente"
COL_ALPI_ID_PORTAIL = "Id Portail"

# ============================================================================
# INDEX COLONNES AMEX CAISSE (Module 1)
# ============================================================================
COL_AMEX_DATE_REGLEMENT    = 1    # Date de règlement
COL_AMEX_DATE_TRANSACTION  = 14   # Date de transaction
COL_AMEX_TYPE              = 4    # Type (SOC/ROC)
COL_AMEX_NUM_REF           = 3    # Numéro de référence
COL_AMEX_NUM_REGLEMENT     = 2    # Numéro de règlement
COL_AMEX_MONTANT_BRUT      = 20   # Total des opérations
COL_AMEX_FRAIS             = 23   # Montant de la remise
COL_AMEX_MONTANT_NET       = 26   # Montant du règlement
COL_AMEX_ROC_ID_TERMINAL   = 7    # ID Terminal AMEX

# ============================================================================
# CONFIGURATIONS MÉTIER
# ============================================================================
STE_DEFAUT = "001"

JOURNAUX = {
    "alma": "VEN", "amex": "CB", "ancv": "CHQ", "banque": "BNQ",
    "ta": "CA", "planet": "VEN", "kiosk": "VEN", "avoirs": "AV"
}

# ============================================================================
# CONFIGURATION TA (BILLETTERIE)
# ============================================================================
TA_COLONNES = {
    "date": "Date", "caisse": "Caisse", "commande": "Commande",
    "montant": "Montant", "libelle": "Libellé"
}
TA_CAISSES_AUTORISEES = ["72", "73", "77"]
TA_LIBELLES_VENTES = ["VENTE", "VENTE SIMPLE", "VENTE CLIENT"]
TA_LIBELLES_ANNULATIONS = ["ANNULATION", "ANNULATION VENTE", "REMBOURSEMENT"]
TA_COMPTE = "580010DS5"

# ============================================================================
# COUPURES MONNAIE (Module 3)
# ============================================================================
COUPURES_BILLETS = {
    500: "500€", 200: "200€", 100: "100€", 50: "50€",
    20: "20€", 10: "10€", 5: "5€"
}

COUPURES_PIECES = {
    2: "2€", 1: "1€", 0.50: "50c", 0.20: "20c",
    0.10: "10c", 0.05: "5c", 0.02: "2c", 0.01: "1c"
}
TOUTES_COUPURES = {**COUPURES_BILLETS, **COUPURES_PIECES}

# ============================================================================
# CONSTANTES MODULE 2
# ============================================================================
ALPILINK_STATUTS_VALIDES = [
    'RECU', 'VALIDÉ', 'ACCEPTÉ', 'CONFIRMÉ',
    'LIVRÉ', 'TRAITÉ', 'EN_COURS'
]

PRO_PARTENAIRES = {
    1: 'Partner A', 2: 'Partner B', 3: 'Partner C'
}

CONTRATS_AMEX = {
    '7770571305': 'AMEX',
    '831103222': 'PLANET',
    '8430996': 'CB'
}

RE_COMMANDE = r'(\d{8})'
REGEX_NUM_COMMANDE = r'^[A-Z]?(\d{8})$'

COMPTA_COLONNES = {
    'date': 'Date', 'libelle': 'Libellé écriture',
    'montant_signe': 'Montant signé', 'debit': 'Débit',
    'credit': 'Crédit', 'journal': 'Journal', 'num_piece': 'N° pièce'
}

COMPTA_JOURNAUX_VE = ['VE', 'VEN', 'VENTE', 'AC', 'ACHAT']
COMPTA_JOURNAUX_ARGENT = [
    'BQ', 'BANQUE', 'CA', 'CAISSE', 'VIR',
    'VIREMENT', 'CHQ', 'CHEQUE'
]

# ============================================================================
# COLONNES DE SORTIE (EXPORT CSV)
# ============================================================================
COLONNES_SORTIE = [
    "STE", "DATE", "COMPTE", "Auxiliaire", "n°pièce",
    "OBJET", "D", "C", "Journal", "Analytique"
]

# ============================================================================
# ALIAS POUR COMPATIBILITÉ
# ============================================================================
COLONNES_COMPTA = COL_COMPTA_DATE, COL_COMPTA_CREDIT, COL_COMPTA_DEBIT, COL_COMPTA_MONTANT, COL_COMPTA_LIBELLE, COL_COMPTA_JOURNAL, COL_COMPTA_SENS, COL_COMPTA_LETTRAGE, COL_COMPTA_PIECE
COLONNES_BANQUE = COL_BANQUE_DATE, COL_BANQUE_COMMAND, COL_BANQUE_MONTANT, COL_BANQUE_TYPE, COL_BANQUE_EMAIL, COL_BANQUE_STATUT, COL_BANQUE_CONTRAT, COL_BANQUE_REMISE, COL_BANQUE_DATE_REMISE
COLONNES_ALPILINK = COL_ALPI_ID_CMD, COL_ALPI_MONTANT, COL_ALPI_STATUT, COL_ALPI_CANAL, COL_ALPI_ID_PORTAIL

# ============================================================================
# UTILITAIRE trouver_colonnes
# ============================================================================
def trouver_colonnes(df: pd.DataFrame, mapping: dict) -> dict:
    """
    Détecte les colonnes d'un DataFrame selon un mapping de noms possibles.

    Args:
        df: DataFrame pandas
        mapping: dict {colonne_cible: [noms_possibles]}

    Returns:
        dict {colonne_cible: nom_colonne_trouvee}
    """
    result = {}
    cols_lower = [str(c).lower().strip() for c in df.columns]

    for cible, possibles in mapping.items():
        for possible in possibles:
            if possible.lower() in cols_lower:
                idx = cols_lower.index(possible.lower())
                result[cible] = df.columns[idx]
                break

    return result

# ============================================================================
# EXPORT
# ============================================================================
__all__ = [
    # Compta
    "COL_COMPTA_DATE", "COL_COMPTA_CREDIT", "COL_COMPTA_DEBIT",
    "COL_COMPTA_MONTANT", "COL_COMPTA_LIBELLE", "COL_COMPTA_JOURNAL",
    "COL_COMPTA_SENS", "COL_COMPTA_LETTRAGE", "COL_COMPTA_PIECE",

    # Banque
    "COL_BANQUE_DATE", "COL_BANQUE_COMMAND", "COL_BANQUE_MONTANT",
    "COL_BANQUE_TYPE", "COL_BANQUE_EMAIL", "COL_BANQUE_STATUT",
    "COL_BANQUE_CONTRAT", "COL_BANQUE_REMISE", "COL_BANQUE_DATE_REMISE",

    # Alpilink
    "COL_ALPI_ID_CMD", "COL_ALPI_MONTANT", "COL_ALPI_STATUT",
    "COL_ALPI_CANAL", "COL_ALPI_ID_PORTAIL",

    # AMEX CAISSE
    "COL_AMEX_DATE_REGLEMENT", "COL_AMEX_DATE_TRANSACTION",
    "COL_AMEX_TYPE", "COL_AMEX_NUM_REF", "COL_AMEX_NUM_REGLEMENT",
    "COL_AMEX_MONTANT_BRUT", "COL_AMEX_FRAIS", "COL_AMEX_MONTANT_NET",
    "COL_AMEX_ROC_ID_TERMINAL",

    # Métier
    "STE_DEFAUT", "JOURNAUX", "CONTRATS_AMEX",

    # TA
    "TA_COLONNES", "TA_CAISSES_AUTORISEES", "TA_LIBELLES_VENTES",
    "TA_LIBELLES_ANNULATIONS", "TA_COMPTE",

    # Sortie
    "COLONNES_SORTIE",

    # Module 2
    "ALPILINK_STATUTS_VALIDES", "PRO_PARTENAIRES",
    "RE_COMMANDE", "COMPTA_COLONNES", "COMPTA_JOURNAUX_VE",
    "COMPTA_JOURNAUX_ARGENT", "REGEX_NUM_COMMANDE",

    # Alias
    "COLONNES_COMPTA", "COLONNES_BANQUE", "COLONNES_ALPILINK",

    # Module 3
    "COUPURES_BILLETS", "COUPURES_PIECES", "TOUTES_COUPURES",

    # Utilitaires
    "trouver_colonnes",
]
