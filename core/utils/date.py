# core/utils/date.py
"""
Utilitaires pour les dates.
"""

from datetime import datetime, timedelta
from typing import Optional, Union

# ═══════════════════════════════════════════════════════════════════════════════
# FORMATS DE DATE
# ═══════════════════════════════════════════════════════════════════════════════

FORMAT_DATE_FR = "%d/%m/%Y"  # 15/12/2023
FORMAT_DATE_ISO = "%Y-%m-%d"  # 2023-12-15
FORMAT_DATE_COMPTA = "%d/%m/%Y"  # Format comptable français
FORMAT_DATETIME_ISO = "%Y-%m-%d %H:%M:%S"


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSION DE DATES
# ═══════════════════════════════════════════════════════════════════════════════

def formater_date(date_str: Union[str, datetime], format_sortie: str = FORMAT_DATE_FR) -> Optional[str]:
    """
    Convertit une date en string formatée.

    Args:
        date_str: Date en string (format détecté auto) ou datetime
        format_sortie: Format de sortie (défaut: DD/MM/YYYY)

    Returns:
        String formatée ou None si invalide

    Example:
        >>> formater_date("2023-12-15")
        '15/12/2023'
        >>> formater_date("15/12/2023")
        '15/12/2023'
    """

    if isinstance(date_str, datetime):
        return date_str.strftime(format_sortie)

    if not isinstance(date_str, str):
        return None

    date_str = date_str.strip()

    # Essayer différents formats
    formats_entree = [
        "%Y-%m-%d",  # ISO
        "%d/%m/%Y",  # Français
        "%d-%m-%Y",  # Tirets
        "%Y/%m/%d",  # Inverse
        "%d%m%Y",  # Sans séparateur
    ]

    for fmt in formats_entree:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime(format_sortie)
        except ValueError:
            continue

    return None


def formater_date_ecriture(
        date_transaction: Union[str, datetime],
        jours_decalage: int = 0,
        format_sortie: str = FORMAT_DATE_FR
) -> Optional[str]:
    """
    Formatte une date d'écriture comptable (date de transaction + décalage).

    ALMA : date_ecriture = date_transaction + 8 jours

    Args:
        date_transaction: Date de transaction
        jours_decalage: Nombre de jours à ajouter (défaut: 0)
        format_sortie: Format de sortie (défaut: DD/MM/YYYY)

    Returns:
        String formatée ou None si invalide

    Example:
        >>> formater_date_ecriture("2023-12-15", jours_decalage=8)
        '23/12/2023'
    """

    # Convertir en datetime
    if isinstance(date_transaction, str):
        date_transaction = date_transaction.strip()

        formats_entree = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
        ]

        dt = None
        for fmt in formats_entree:
            try:
                dt = datetime.strptime(date_transaction, fmt)
                break
            except ValueError:
                continue

        if dt is None:
            return None

    elif isinstance(date_transaction, datetime):
        dt = date_transaction
    else:
        return None

    # Ajouter le décalage
    if jours_decalage != 0:
        dt = dt + timedelta(days=jours_decalage)

    return dt.strftime(format_sortie)


def ajouter_jours(date_str: Union[str, datetime], jours: int) -> Optional[datetime]:
    """
    Ajoute des jours à une date.

    Args:
        date_str: Date initiale
        jours: Nombre de jours à ajouter

    Returns:
        datetime avec le décalage
    """

    if isinstance(date_str, str):
        dt = formater_date(date_str)
        if not dt:
            return None
        # Reconvertir en datetime
        dt = datetime.strptime(dt, FORMAT_DATE_FR)
    else:
        dt = date_str

    return dt + timedelta(days=jours)


def extraire_mois_annee(date_str: Union[str, datetime]) -> tuple:
    """
    Extrait mois et année d'une date.

    Returns:
        Tuple (mois, année) ou (None, None)
    """

    if isinstance(date_str, str):
        date_obj = datetime.strptime(formater_date(date_str, FORMAT_DATE_ISO), FORMAT_DATE_ISO)
    else:
        date_obj = date_str

    return (date_obj.month, date_obj.year)


__all__ = [
    "FORMAT_DATE_FR",
    "FORMAT_DATE_ISO",
    "FORMAT_DATE_COMPTA",
    "formater_date",
    "formater_date_ecriture",
    "ajouter_jours",
    "extraire_mois_annee",
]


def date_en_cle(date_str: Union[str, datetime]) -> str:
    """
    Convertit une date en clé format : AAAA-MM-DD

    Utilisé pour générer les numéros de pièce comptable.

    Args:
        date_str: Date en string ou datetime

    Returns:
        String format clé (ex: "2026-02-02")

    Exemples:
        >>> date_en_cle("02/02/2026")
        '2026-02-02'
        >>> date_en_cle("2026-02-02")
        '2026-02-02'
    """
    if isinstance(date_str, datetime):
        return date_str.strftime("%Y-%m-%d")

    # Formater d'abord en ISO
    date_formatee = formater_date(date_str, FORMAT_DATE_ISO)

    if date_formatee is None:
        return ""

    return date_formatee


__all__ = [
    "FORMAT_DATE_FR",
    "FORMAT_DATE_ISO",
    "FORMAT_DATE_COMPTA",
    "formater_date",
    "formater_date_ecriture",
    "ajouter_jours",
    "extraire_mois_annee",
    "date_en_cle",  # ✅ AJOUT
]