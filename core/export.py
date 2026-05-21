# Dans core/export.py (nouveau fichier)

import csv
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def _exporter_csv_remise(self):
    """Exporte les caisses vérifiées en CSV pour la remise banque"""
    from core.verification import charger_verification
    import csv
    from pathlib import Path

    date_str = self.date_var.get().strip()

    # Charger les données vérifiées
    verif_data = charger_verification(date_str)

    if not verif_data or not verif_data.get('caisses_verif'):
        messagebox.showwarning(
            "⚠️ Aucune vérification",
            "Aucune vérification trouvée pour cette date",
            parent=self
        )
        return

    try:
        # ✅ CHEMIN RÉSEAU
        dossier_sortie = Path(
            r"\\share-01.pleney.local\FICHIERS\Finances\Dossier perso - Matth\Application pour la compta\compta_app - Test\sorties\fichiers_compta")

        # Crée le dossier s'il n'existe pas
        dossier_sortie.mkdir(parents=True, exist_ok=True)

        # Détermine le chemin du fichier
        date_clean = date_str.replace('/', '-')
        fichier_sortie = dossier_sortie / f"remise_caisses_{date_clean}.csv"

        with open(fichier_sortie, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')

            # En-têtes
            writer.writerow([
                'STE', 'DATE', 'COMPTE', 'Auxiliaire',
                "n'pièce", 'OBJET', 'D', 'C', 'Journal'
            ])

            date_obj = datetime.strptime(date_str, '%d/%m/%Y').strftime('%d/%m/%Y')
            compte = '580001'
            journal = 'VE'

            caisses_verif = verif_data.get('caisses_verif', {})

            total_billets = 0
            total_pieces = 0

            # CAISSES - 2 LIGNES PAR CAISSE
            for num_caisse in sorted(caisses_verif.keys(),
                                     key=lambda x: int(x.replace('Caisse ', ''))):
                caisse_data = caisses_verif[num_caisse]

                montant_billets = caisse_data.get('total_billets', 0)
                montant_pieces = caisse_data.get('total_pieces', 0)

                # Ligne BILLETS (DÉBIT)
                if montant_billets > 0:
                    writer.writerow([
                        'DLM',
                        date_obj,
                        compte,
                        '',
                        f"Billets {num_caisse}",
                        f"Encaissement espèce du {date_obj}",
                        f"{montant_billets:.2f}",  # ← DÉBIT
                        '',  # ← CRÉDIT vide
                        journal
                    ])
                    total_billets += montant_billets

                # Ligne PIÈCES (DÉBIT)
                if montant_pieces > 0:
                    writer.writerow([
                        'DLM',
                        date_obj,
                        compte,
                        '',
                        f"Pièces {num_caisse}",
                        f"Encaissement espèce du {date_obj}",
                        f"{montant_pieces:.2f}",  # ← DÉBIT
                        '',  # ← CRÉDIT vide
                        journal
                    ])
                    total_pieces += montant_pieces

            # CONTREPARTIE - TOTAL (CRÉDIT)
            total_general = total_billets + total_pieces

            if total_general > 0:
                writer.writerow([
                    'DLM',
                    date_obj,
                    compte,
                    '',
                    'Total',
                    f"Total {date_obj}",
                    '',  # ← DÉBIT vide
                    f"{total_general:.2f}",  # ← CRÉDIT
                    journal
                ])

        messagebox.showinfo(
            "✅ Succès",
            f"Export réussi :\n{fichier_sortie}",
            parent=self
        )
        logger.info(f"Export CSV remise : {fichier_sortie}")

    except Exception as e:
        messagebox.showerror(
            "❌ Erreur",
            f"Erreur lors de l'export :\n{e}",
            parent=self
        )
        logger.error(f"Erreur export CSV : {e}")
