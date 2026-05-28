"""
Utilitaires pour les calculs monétaires.
"""

import re
from typing import Optional, Union


def to_float(val) -> Optional[float]:
    """
    Convertit une valeur en float de manière robuste.

    Args:
        val: Valeur à convertir (str, int, float, etc.)

    Returns:
        float ou None si conversion impossible

    Exemples:
        >>> to_float("123.45")
        123.45
        >>> to_float("123,45")
        123.45
        >>> to_float(None)
        None
    """
    if val is None or val == "":
        return None

    try:
        # Si c'est déjà un nombre
        if isinstance(val, (int, float)):
            return float(val)

        # Convertir string
        val_str = str(val).strip()
        if not val_str:
            return None

        # Remplacer virgule par point
        val_str = val_str.replace(",", ".")

        # Supprimer les espaces
        val_str = val_str.replace(" ", "")

        return float(val_str)

    except (ValueError, TypeError):
        return None


def nettoyer_montant(montant: Union[str, float, int, None]) -> str:
    """
    Nettoie un montant brut : enlève €, espaces, symboles, etc.

    Convertit aussi les virgules en points pour faciliter les calculs.

    Args:
        montant: Montant brut à nettoyer (str, float, int, None)

    Returns:
        Montant nettoyé en string (ex: "123.45")

    Exemples:
        >>> nettoyer_montant("123,45 €")
        '123.45'
        >>> nettoyer_montant("1 000,50€")
        '1000.50'
        >>> nettoyer_montant(None)
        '0'
        >>> nettoyer_montant(123.45)
        '123.45'
    """
    if montant is None or montant == "":
        return "0"

    try:
        # Convertir en string
        montant_str = str(montant).strip()

        # Enlever les symboles € et autres devises
        montant_str = montant_str.replace("€", "").replace("$", "").replace("£", "")

        # Enlever les espaces
        montant_str = montant_str.replace(" ", "")

        # Remplacer virgule française par point
        montant_str = montant_str.replace(",", ".")

        # Enlever les caractères non numériques sauf le point et le signe négatif
        montant_str = re.sub(r"[^\d.\-]", "", montant_str)

        # Valider que c'est un nombre valide
        if montant_str and montant_str != "-":
            float(montant_str)  # Test si c'est convertible
            return montant_str
        else:
            return "0"

    except (ValueError, TypeError, AttributeError):
        return "0"


def format_montant(montant: Union[float, int, str, None], devises: str = "€") -> str:
    """
    Formate un montant pour l'affichage.

    Args:
        montant: Montant à formater
        devises: Symbole devise (défaut: "€")

    Returns:
        Montant formaté (ex: "123,45 €")

    Exemples:
        >>> format_montant(123.456)
        '123,46 €'
        >>> format_montant(1000.5)
        '1 000,50 €'
        >>> format_montant("123,45")
        '123,45 €'
    """
    if montant is None or montant == "":
        return "0,00 €"

    try:
        # Convertir en float
        montant = to_float(montant)
        if montant is None:
            return "0,00 €"

        montant = float(montant)
    except (ValueError, TypeError):
        return "0,00 €"

    # Formater avec 2 décimales
    montant_str = f"{montant:.2f}".replace(".", ",")

    # Ajouter séparateur de milliers
    parties = montant_str.split(",")
    partie_entiere = parties[0]
    partie_decimale = parties[1] if len(parties) > 1 else "00"

    # Ajouter espaces tous les 3 chiffres (de droite à gauche)
    partie_entiere_inversee = partie_entiere[::-1]
    partie_entiere_espacee = " ".join(
        partie_entiere_inversee[i:i + 3]
        for i in range(0, len(partie_entiere_inversee), 3)
    )
    partie_entiere = partie_entiere_espacee[::-1]

    return f"{partie_entiere},{partie_decimale} {devises}"


def arrondir_montant(montant: Union[float, int, str, None], decimales: int = 2) -> float:
    """
    Arrondit un montant à N décimales.

    Args:
        montant: Montant à arrondir
        decimales: Nombre de décimales (défaut: 2)

    Returns:
        Montant arrondi

    Exemples:
        >>> arrondir_montant(123.456)
        123.46
        >>> arrondir_montant("123,456")
        123.46
    """
    if montant is None or montant == "":
        return 0.0

    try:
        montant = to_float(montant)
        if montant is None:
            return 0.0
        return round(float(montant), decimales)
    except (ValueError, TypeError):
        return 0.0


__all__ = ["to_float", "format_montant", "arrondir_montant", "nettoyer_montant"]
