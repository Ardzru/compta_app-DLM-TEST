# core/utils/colonnes.py
"""
Constantes pour les noms de colonnes.
"""

# ─── COLONNES COMPTA ──────────────────────────────────────────────
COL_COMPTA_DATE     = "Date"
COL_COMPTA_CREDIT   = "Crédit"
COL_COMPTA_DEBIT    = "Débit"
COL_COMPTA_MONTANT  = "Montant signé"
COL_COMPTA_LIBELLE  = "Libellé écriture"
COL_COMPTA_JOURNAL  = "Journal"
COL_COMPTA_SENS     = "Sens"
COL_COMPTA_LETTRAGE = "Lettrage"
COL_COMPTA_PIECE    = "Libellé écriture"

# ─── COLONNES BANQUE ──────────────────────────────────────────────
COL_BANQUE_DATE        = "Date du paiement"
COL_BANQUE_COMMAND     = "Commande"
COL_BANQUE_MONTANT     = "Montant du paiement"
COL_BANQUE_TYPE        = "Moyen de paiement"
COL_BANQUE_EMAIL       = "E-mail acheteur"
COL_BANQUE_STATUT      = "Statut rapprochement"
COL_BANQUE_CONTRAT     = "Contrat commerçant"
COL_BANQUE_REMISE      = "N° remise"
COL_BANQUE_DATE_REMISE = "Date remise"

# ─── COLONNES ALPILINK ────────────────────────────────────────────
COL_ALPI_ID_CMD     = "Id Commande"
COL_ALPI_MONTANT    = "Prix Total"
COL_ALPI_STATUT     = "Statut"
COL_ALPI_CANAL      = "Canal de vente"
COL_ALPI_ID_PORTAIL = "Id Portail"

# ═══════════════════════════════════════════════════════════════════════════════
# SOCIÉTÉ ET JOURNAUX
# ═══════════════════════════════════════════════════════════════════════════════

STE_DEFAUT = "001"

JOURNAUX = {
    "alma": "VEN",           # Ventes ALMA
    "amex": "CB",            # Cartes bancaires AMEX
    "ancv": "CHQ",           # Chèques ANCV
    "banque": "BNQ",         # Virements bancaires
    "ta": "CA",              # Porte-monnaie TA
    "planet": "VEN",         # Ventes Planet
    "kiosk": "VEN",          # Kiosk Photo
    "avoirs": "AV",          # Avoirs clients
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION TA (BILLETTERIE / CAISSE)
# ═══════════════════════════════════════════════════════════════════════════════

TA_COLONNES = {
    "date":     "Date",          # Colonne de la date
    "caisse":   "Caisse",        # Numéro de caisse
    "commande": "Commande",      # Numéro de commande
    "montant":  "Montant",       # Montant en euros
    "libelle":  "Libellé",       # Type de mouvement
}

TA_CAISSES_AUTORISEES = ["72", "73", "77"]

TA_LIBELLES_VENTES = [
    "VENTE",
    "VENTE SIMPLE",
    "VENTE CLIENT",
]

TA_LIBELLES_ANNULATIONS = [
    "ANNULATION",
    "ANNULATION VENTE",
    "REMBOURSEMENT",
]

TA_COMPTE = "580010DS5"  # Compte transit pour TA

# ═══════════════════════════════════════════════════════════════════════════════
# COLONNES DE SORTIE (EXPORT CSV COMPTABLE)
# ═══════════════════════════════════════════════════════════════════════════════

COLONNES_SORTIE = [
    "STE",
    "DATE",
    "COMPTE",
    "Auxiliaire",
    "n°pièce",
    "OBJET",
    "D",
    "C",
    "Journal",
    "Analytique",
]

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES POUR LES HANDLERS (MODULE 2)
# ═══════════════════════════════════════════════════════════════════════════════

# ─── ALPILINK ──────────────────────────────────────────────────────────────────
ALPILINK_STATUTS_VALIDES = [
    'RECU',
    'VALIDÉ',
    'ACCEPTÉ',
    'CONFIRMÉ',
    'LIVRÉ',
    'TRAITÉ',
    'EN_COURS',
]

PRO_PARTENAIRES = {
    1: 'Partner A',
    2: 'Partner B',
    3: 'Partner C',
    # À compléter avec tes vrais partenaires
}

# ─── BANQUE ────────────────────────────────────────────────────────────────────
CONTRATS_AMEX = {
    '7770571305': 'AMEX',
    '831103222': 'PLANET',
    '8430996': 'CB',
}

RE_COMMANDE = r'(\d{8})'  # Regex pour extraire 8 chiffres

# ─── COMPTA ────────────────────────────────────────────────────────────────────
COMPTA_COLONNES = {
    'date': 'Date',
    'libelle': 'Libellé écriture',
    'montant_signe': 'Montant signé',
    'debit': 'Débit',
    'credit': 'Crédit',
    'journal': 'Journal',
    'num_piece': 'N° pièce',
}

COMPTA_JOURNAUX_VE = [
    'VE',
    'VEN',
    'VENTE',
    'AC',
    'ACHAT',
]

COMPTA_JOURNAUX_ARGENT = [
    'BQ',
    'BANQUE',
    'CA',
    'CAISSE',
    'VIR',
    'VIREMENT',
    'CHQ',
    'CHEQUE',
]

# ─── REGEX ────────────────────────────────────────────────────────────────────
REGEX_NUM_COMMANDE = r'^[A-Z]?(\d{8})$'

# ═══════════════════════════════════════════════════════════════════════════════
# ALIAS (compatibilité)
# ═══════════════════════════════════════════════════════════════════════════════

COLONNES_COMPTA = COMPTA_COLONNES
COLONNES_BANQUE = [
    COL_BANQUE_DATE, COL_BANQUE_COMMAND, COL_BANQUE_MONTANT,
    COL_BANQUE_TYPE, COL_BANQUE_EMAIL, COL_BANQUE_STATUT,
    COL_BANQUE_CONTRAT, COL_BANQUE_REMISE, COL_BANQUE_DATE_REMISE,
]
COLONNES_ALPILINK = [
    COL_ALPI_ID_CMD, COL_ALPI_MONTANT, COL_ALPI_STATUT,
    COL_ALPI_CANAL, COL_ALPI_ID_PORTAIL,
]

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

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
]

# core/utils/colonnes.py

# ========================================
# COUPURES MONNAIE (Module 3 - Caisses)
# ========================================

COUPURES_BILLETS = {
    500: "500€",
    200: "200€",
    100: "100€",
    50: "50€",
    20: "20€",
    10: "10€",
    5: "5€",
}

COUPURES_PIECES = {
    2: "2€",
    1: "1€",
    0.50: "50c",
    0.20: "20c",
    0.10: "10c",
    0.05: "5c",
    0.02: "2c",
    0.01: "1c",
}

# Tous les montants combinés
TOUTES_COUPURES = {**COUPURES_BILLETS, **COUPURES_PIECES}

__all__ = [
    "COUPURES_BILLETS",
    "COUPURES_PIECES",
    "TOUTES_COUPURES",
]
