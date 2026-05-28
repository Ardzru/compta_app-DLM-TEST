# modules/module_3/__init__.py
"""
Module 3 - Gestion des caisses, stocks et remises
"""

from modules.module_3.verification import (
    calculer_total_pieces,
    calculer_total_billets,
    charger_verification,
    sauvegarder_verification,
    recalculer_totaux_verification,
)

from modules.module_3.stock import (
    alimenter_depuis_caisse,
    get_stock,
    get_total_especes,
    get_total_cheques_vac,
    get_total_cheques,
    get_total_ancv,
    get_total_general,
    retirer_remise,
    modifier_stock_direct,
    reset_stock,
    sauvegarder_stock,
)

from modules.module_3.remises import (
    ajouter_remise,
    marquer_remis,
    valider_remise_stock,
    get_remise,
    get_remises_en_attente,
    get_remises_non_remises_banque,
    get_remises_par_caisse,
    get_remises_par_type,
    get_remises_par_date,
    get_historique,
    get_stats_remises,
    supprimer_remise,
    reset_remises,
)

__all__ = [
    # verification
    "calculer_total_pieces",
    "calculer_total_billets",
    "charger_verification",
    "sauvegarder_verification",
    "recalculer_totaux_verification",

    # stock
    "alimenter_depuis_caisse",
    "get_stock",
    "get_total_especes",
    "get_total_cheques_vac",
    "get_total_cheques",
    "get_total_ancv",
    "get_total_general",
    "retirer_remise",
    "modifier_stock_direct",
    "reset_stock",
    "sauvegarder_stock",

    # remises
    "ajouter_remise",
    "marquer_remis",
    "valider_remise_stock",
    "get_remise",
    "get_remises_en_attente",
    "get_remises_non_remises_banque",
    "get_remises_par_caisse",
    "get_remises_par_type",
    "get_remises_par_date",
    "get_historique",
    "get_stats_remises",
    "supprimer_remise",
    "reset_remises",
]
