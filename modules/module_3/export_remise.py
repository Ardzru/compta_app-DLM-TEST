# modules/module_3/export_remise.py
"""
Exporte les remises de caisses en fichier CSV pour la comptabilité.
"""

import csv
from pathlib import Path
from config import logger
from core.utils.montant import format_montant
from core.utils.colonnes import STE_DEFAUT, JOURNAUX, COLONNES_SORTIE
from modules.module_3 import verification

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES COMPTABLES
# ══════════════════════════════════════════════════════════════════════════════

COMPTE_CAISSE = "580001"


# JOURNAL et COLONNES viennent de core/utils_colonnes

# ══════════════════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

def exporter_remise_csv(
        date_str: str,
        dossier_sortie: Path = None
) -> Path:
    """
    Exporte les caisses vérifiées en CSV pour la remise banque.

    Args:
        date_str (str): Date au format "dd/mm/YYYY" (ex: "20/05/2026")
        dossier_sortie (Path, optional): Chemin custom.
                                        Sinon utilise config.DOSSIER_SORTIE

    Returns:
        Path: Chemin du fichier créé

    Raises:
        ValueError: Si aucune vérification trouvée
        IOError: Si erreur écriture fichier

    Exemple:
        chemin = exporter_remise_csv("20/05/2026")
        → Path("...remise_caisses_20-05-2026.csv")
    """

    # Charger les données vérifiées
    verif_data = verification.charger_verification(date_str)

    if not verif_data or not verif_data.get('caisses_verif'):
        logger.warning(f"⚠️ Aucune vérification trouvée pour {date_str}")
        raise ValueError(f"Aucune vérification trouvée pour {date_str}")

    # Si dossier_sortie pas fourni, utiliser config
    if dossier_sortie is None:
        from config import DOSSIER_SORTIE
        dossier_sortie = DOSSIER_SORTIE

    try:
        # Crée le dossier s'il n'existe pas
        dossier_sortie.mkdir(parents=True, exist_ok=True)

        # Détermine le chemin du fichier
        date_clean = date_str.replace('/', '-')
        fichier_sortie = dossier_sortie / f"remise_caisses_{date_clean}.csv"

        with open(fichier_sortie, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')

            # En-têtes
            writer.writerow(COLONNES_SORTIE)

            caisses_verif = verif_data.get('caisses_verif', {})

            total_billets = 0.0
            total_pieces = 0.0

            # ─── ÉCRITURES PAR CAISSE (DÉBITS) ─────────────────────────────────
            for num_caisse in sorted(
                    caisses_verif.keys(),
                    key=lambda x: int(x.replace('Caisse ', '')) if 'Caisse' in x else 0
            ):
                caisse_data = caisses_verif[num_caisse]

                from core.utils.montant import to_float
                montant_billets = to_float(caisse_data.get('total_billets', 0))
                montant_pieces = to_float(caisse_data.get('total_pieces', 0))

                # Ligne BILLETS (DÉBIT)
                if montant_billets > 0:
                    writer.writerow([
                        STE_DEFAUT,
                        date_str,
                        COMPTE_CAISSE,
                        '',
                        f"Billets {num_caisse}",
                        f"Encaissement espèce du {date_str}",
                        format_montant(montant_billets),  # ← DÉBIT
                        '',  # ← CRÉDIT vide
                        JOURNAUX["ventes"],
                        "",  # Analytique
                    ])
                    total_billets += montant_billets

                # Ligne PIÈCES (DÉBIT)
                if montant_pieces > 0:
                    writer.writerow([
                        STE_DEFAUT,
                        date_str,
                        COMPTE_CAISSE,
                        '',
                        f"Pièces {num_caisse}",
                        f"Encaissement espèce du {date_str}",
                        format_montant(montant_pieces),  # ← DÉBIT
                        '',  # ← CRÉDIT vide
                        JOURNAUX["ventes"],
                        "",  # Analytique
                    ])
                    total_pieces += montant_pieces

            # ─── CONTREPARTIE - TOTAL (CRÉDIT) ────────────────────────────────
            total_general = total_billets + total_pieces

            if total_general > 0:
                writer.writerow([
                    STE_DEFAUT,
                    date_str,
                    COMPTE_CAISSE,
                    '',
                    'Total',
                    f"Total {date_str}",
                    '',  # ← DÉBIT vide
                    format_montant(total_general),  # ← CRÉDIT
                    JOURNAUX["ventes"],
                    "",  # Analytique
                ])

        logger.info(f"✅ Export CSV remise : {fichier_sortie.name}")
        logger.info(f"   📝 Billets: {format_montant(total_billets)}€")
        logger.info(f"   📝 Pièces: {format_montant(total_pieces)}€")
        logger.info(f"   💰 Total: {format_montant(total_general)}€")

        return fichier_sortie

    except Exception as e:
        logger.error(f"❌ Erreur export CSV remise : {e}")
        raise IOError(f"Impossible d'exporter : {e}")
