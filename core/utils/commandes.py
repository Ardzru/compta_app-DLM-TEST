# core/utils/commandes.py
"""
Utilitaires pour traiter les numéros de commandes.
"""

import re
from typing import Optional

# Regex pour les commandes valides
RE_CMD = re.compile(r'^(?:\d{8}|[A-Za-z]{2}\d{7})$')


def normaliser_cmd(valeur) -> Optional[str]:
    """
    Normalise et valide un numéro de commande.

    Format acceptés:
    - 8 chiffres: 12345678
    - 2 lettres + 7 chiffres: AB1234567

    Args:
        valeur: Numéro de commande à normaliser

    Returns:
        Numéro normalisé (str) ou None si invalide

    Exemples:
        >>> normaliser_cmd("12345678")
        '12345678'
        >>> normaliser_cmd("AB1234567")
        'AB1234567'
        >>> normaliser_cmd("INVALID")
        None
    """
    if valeur is None or valeur == "":
        return None

    cmd_str = str(valeur).strip().upper()

    if RE_CMD.match(cmd_str):
        return cmd_str

    return None


def extraire_8_chiffres(valeur) -> Optional[str]:
    """
    Extrait les 8 premiers chiffres d'une chaîne.

    Exemples:
        >>> extraire_8_chiffres("ABC12345678DEF")
        '12345678'
    """
    if valeur is None:
        return None

    chiffres = re.findall(r'\d', str(valeur))

    if len(chiffres) >= 8:
        return "".join(chiffres[:8])

    return None


def est_commande_valide(valeur) -> bool:
    """
    Vérifie si une valeur est une commande valide.
    """
    return normaliser_cmd(valeur) is not None


__all__ = ["normaliser_cmd", "extraire_8_chiffres", "est_commande_valide", "RE_CMD"]
