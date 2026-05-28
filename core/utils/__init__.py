# core/utils/__init__.py
"""
Utilitaires centralisés pour l'application comptable.
"""

from .colonnes import (
    # Compta
    COL_COMPTA_DATE, COL_COMPTA_CREDIT, COL_COMPTA_DEBIT,
    COL_COMPTA_MONTANT, COL_COMPTA_LIBELLE, COL_COMPTA_JOURNAL,
    COL_COMPTA_SENS, COL_COMPTA_LETTRAGE, COL_COMPTA_PIECE,
    # Banque
    COL_BANQUE_DATE, COL_BANQUE_COMMAND, COL_BANQUE_MONTANT,
    COL_BANQUE_TYPE, COL_BANQUE_EMAIL, COL_BANQUE_STATUT,
    COL_BANQUE_CONTRAT, COL_BANQUE_REMISE, COL_BANQUE_DATE_REMISE,
    # Alpilink
    COL_ALPI_ID_CMD, COL_ALPI_MONTANT, COL_ALPI_STATUT,
    COL_ALPI_CANAL, COL_ALPI_ID_PORTAIL,
    # TA (Billetterie)
    TA_COLONNES, TA_CAISSES_AUTORISEES,
    TA_LIBELLES_VENTES, TA_LIBELLES_ANNULATIONS, TA_COMPTE,
    # Métier
    STE_DEFAUT, JOURNAUX, CONTRATS_AMEX,
    # Sortie
    COLONNES_SORTIE,
)

from .date import (
    FORMAT_DATE_FR,
    FORMAT_DATE_ISO,
    FORMAT_DATE_COMPTA,
    formater_date,
    formater_date_ecriture,
    ajouter_jours,
    extraire_mois_annee,
)

from .montant import (
    to_float,
    format_montant,
    arrondir_montant,
    nettoyer_montant,
)

from .convert_xls import (  # ✅ CHANGE: convert_xls au lieu de convertisseur_xls
    convertir_xls_en_xlsx,
)

__all__ = [
    # Colonnes - Compta
    "COL_COMPTA_DATE", "COL_COMPTA_CREDIT", "COL_COMPTA_DEBIT",
    "COL_COMPTA_MONTANT", "COL_COMPTA_LIBELLE", "COL_COMPTA_JOURNAL",
    "COL_COMPTA_SENS", "COL_COMPTA_LETTRAGE", "COL_COMPTA_PIECE",
    # Colonnes - Banque
    "COL_BANQUE_DATE", "COL_BANQUE_COMMAND", "COL_BANQUE_MONTANT",
    "COL_BANQUE_TYPE", "COL_BANQUE_EMAIL", "COL_BANQUE_STATUT",
    "COL_BANQUE_CONTRAT", "COL_BANQUE_REMISE", "COL_BANQUE_DATE_REMISE",
    # Colonnes - Alpilink
    "COL_ALPI_ID_CMD", "COL_ALPI_MONTANT", "COL_ALPI_STATUT",
    "COL_ALPI_CANAL", "COL_ALPI_ID_PORTAIL",
    # Colonnes - TA
    "TA_COLONNES", "TA_CAISSES_AUTORISEES",
    "TA_LIBELLES_VENTES", "TA_LIBELLES_ANNULATIONS", "TA_COMPTE",
    # Colonnes - Métier
    "STE_DEFAUT", "JOURNAUX", "CONTRATS_AMEX", "COLONNES_SORTIE",
    # Date
    "FORMAT_DATE_FR", "FORMAT_DATE_ISO", "FORMAT_DATE_COMPTA",
    "formater_date", "formater_date_ecriture", "ajouter_jours",
    "extraire_mois_annee",
    # Montant
    "to_float", "format_montant", "arrondir_montant", "nettoyer_montant",
    # Fichiers
    "convertir_xls_en_xlsx",
]
