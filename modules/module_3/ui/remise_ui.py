"""
Module 3 UI - Gestion des remises en banque
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from pathlib import Path
import logging
import csv
import json

# ✅ IMPORTS RELATIFS
from ..verification import charger_verification
from ..remises import (
    ajouter_remise,
    get_remises_par_date,
    marquer_remis,
    get_stats_remises,
    valider_remise_stock
)

logger = logging.getLogger(__name__)

class RemiseUI(tk.Frame):
    """Interface de gestion des remises en banque"""

    def __init__(self, parent):
        super().__init__(parent, bg="#1e1e2e")
        self.pack(fill="both", expand=True)
        self.date_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        self.remises_data = {}

        self._build_ui()
        self._charger_remises()

    def _build_ui(self):
        """Construit l'interface des remises"""

        # ===== HEADER =====
        header = tk.Frame(self, bg="#313244", pady=10)
        header.pack(fill="x")

        tk.Label(
            header,
            text="🏦 Remises en banque",
            bg="#313244", fg="#89b4fa",
            font=("Segoe UI", 14, "bold")
        ).pack()

        # ===== CONTENU PRINCIPAL =====
        content = tk.Frame(self, bg="#1e1e2e")
        content.pack(fill="both", expand=True, padx=12, pady=12)

        # --- Sélecteur de date ---
        date_frame = tk.Frame(content, bg="#1e1e2e")
        date_frame.pack(fill="x", pady=10)

        tk.Label(
            date_frame,
            text="Date:",
            bg="#1e1e2e", fg="#cdd6f4",
            font=("Segoe UI", 10)
        ).pack(side="left", padx=5)

        tk.Entry(
            date_frame,
            textvariable=self.date_var,
            font=("Segoe UI", 10),
            width=15
        ).pack(side="left", padx=5)

        tk.Button(
            date_frame,
            text="🔄 Charger",
            bg="#89b4fa", fg="#1e1e2e",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            command=self._charger_remises
        ).pack(side="left", padx=5)

        # --- Tableau des remises ---
        self._build_tableau_remises(content)

        # --- Boutons d'action ---
        button_frame = tk.Frame(content, bg="#1e1e2e")
        button_frame.pack(fill="x", pady=20)

        tk.Button(
            button_frame,
            text="✅ Créer remise espèces",
            command=self._creer_remise_especes,
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            padx=15, pady=10,
            cursor="hand2"
        ).pack(side="left", padx=10)

        tk.Button(
            button_frame,
            text="🏪 Créer remise chèques",
            command=self._creer_remise_cheques,
            bg="#cba6f7", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            padx=15, pady=10,
            cursor="hand2"
        ).pack(side="left", padx=10)

        tk.Button(
            button_frame,
            text="📊 Exporter CSV",
            command=self._exporter_csv,
            bg="#89b4fa", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            padx=15, pady=10,
            cursor="hand2"
        ).pack(side="left", padx=10)

    def _build_tableau_remises(self, parent):
        """Construit le tableau des remises"""
        frame = tk.Frame(parent, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, pady=10)

        scroll = ttk.Scrollbar(frame, orient="vertical")
        scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(
            frame,
            columns=["ID", "Type", "Montant", "Statut", "Banque"],
            height=10,
            yscrollcommand=scroll.set
        )
        scroll.config(command=self.tree.yview)

        self.tree.column("#0", width=0, stretch=False)
        self.tree.column("ID", anchor="center", width=50)
        self.tree.column("Type", anchor="center", width=120)
        self.tree.column("Montant", anchor="e", width=100)
        self.tree.column("Statut", anchor="center", width=100)
        self.tree.column("Banque", anchor="center", width=80)

        self.tree.heading("#0", text="")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Montant", text="Montant")
        self.tree.heading("Statut", text="Statut")
        self.tree.heading("Banque", text="Banque")

        style = ttk.Style()
        style.configure("Treeview", background="#313244", foreground="#cdd6f4")
        style.configure("Treeview.Heading", background="#45475a", foreground="#89b4fa")

        self.tree.tag_configure("valide", background="#2a3a2a")
        self.tree.tag_configure("attente", background="#3a2a2a")
        self.tree.tag_configure("banque", background="#2a2a3a")

        self.tree.pack(fill="both", expand=True)

    def _charger_remises(self):
        """Charge les remises de la date sélectionnée"""
        date_str = self.date_var.get().strip()

        try:
            # Charger les vérifications du jour
            verif_data = charger_verification(date_str)
            if not verif_data:
                logger.warning(f"⚠️ Aucune vérification pour {date_str}")
                self._afficher_remises({})
                return

            # Charger les remises existantes pour cette date
            remises = get_remises_par_date(date_str)
            self.remises_data = {r['id']: r for r in remises}

            logger.info(f"✅ {len(remises)} remise(s) chargée(s)")
            self._afficher_remises(self.remises_data)

        except Exception as e:
            logger.error(f"❌ Erreur chargement remises : {e}")
            messagebox.showerror("❌ Erreur", f"Erreur : {e}", parent=self)

    def _afficher_remises(self, remises_dict):
        """Affiche les remises dans le tableau"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not remises_dict:
            return

        for remise_id, remise in remises_dict.items():
            remise_type = remise.get("type", "?")
            montant = remise.get("montant_total", 0)
            valide = "✅ Validée" if remise.get("valide_stock", False) else "⏳ En attente"
            banque = "🏦 Oui" if remise.get("remis_banque", False) else "❌ Non"

            # Déterminer le tag
            if remise.get("remis_banque", False):
                tag = "banque"
            elif remise.get("valide_stock", False):
                tag = "valide"
            else:
                tag = "attente"

            self.tree.insert(
                "", "end",
                iid=remise_id,
                values=[remise_id, remise_type, f"{montant:.2f} €", valide, banque],
                tags=(tag,)
            )

    def _creer_remise_especes(self):
        """Crée une remise d'espèces"""
        date_str = self.date_var.get().strip()

        try:
            verif_data = charger_verification(date_str)
            if not verif_data or not verif_data.get('caisses_verif'):
                messagebox.showwarning(
                    "⚠️ Aucune vérification",
                    f"Aucune vérification trouvée pour {date_str}",
                    parent=self
                )
                return

            # Calculer total espèces
            total_especes = 0.0
            detail = {}

            for num_caisse, caisse_data in verif_data.get('caisses_verif', {}).items():
                billets = caisse_data.get('total_billets', 0) or 0
                pieces = caisse_data.get('total_pieces', 0) or 0
                total_caisse = float(billets) + float(pieces)

                if total_caisse > 0:
                    detail[num_caisse] = {
                        "billets": float(billets),
                        "pieces": float(pieces),
                        "total": total_caisse
                    }
                    total_especes += total_caisse

            if total_especes == 0:
                messagebox.showwarning(
                    "⚠️ Aucune espèce",
                    "Aucune espèce à remettre",
                    parent=self
                )
                return

            # Créer la remise
            remise_id = ajouter_remise(
                date_caisse=date_str,
                num_caisse="COLLECTIVE",
                type_remise="especes",
                detail=detail,
                remis_banque=False
            )

            # Valider le stock immédiatement
            valider_remise_stock(remise_id)

            messagebox.showinfo(
                "✅ Succès",
                f"Remise #${remise_id} créée\nMontant : {total_especes:.2f} €",
                parent=self
            )

            logger.info(f"✅ Remise espèces créée : #{remise_id}")
            self._charger_remises()

        except Exception as e:
            logger.error(f"❌ Erreur création remise : {e}")
            messagebox.showerror("❌ Erreur", f"Erreur : {e}", parent=self)

    def _creer_remise_cheques(self):
        """Crée une remise de chèques"""
        date_str = self.date_var.get().strip()

        try:
            verif_data = charger_verification(date_str)
            if not verif_data or not verif_data.get('caisses_verif'):
                messagebox.showwarning(
                    "⚠️ Aucune vérification",
                    f"Aucune vérification trouvée pour {date_str}",
                    parent=self
                )
                return

            # TODO: Implémenter logique de chèques
            messagebox.showinfo(
                "ℹ️ À implémenter",
                "Gestion des chèques à venir",
                parent=self
            )

        except Exception as e:
            logger.error(f"❌ Erreur : {e}")
            messagebox.showerror("❌ Erreur", f"Erreur : {e}", parent=self)

    def _exporter_csv(self):
        """Exporte les remises en CSV"""
        date_str = self.date_var.get()

        try:
            verif_data = charger_verification(date_str)
            if not verif_data:
                messagebox.showwarning(
                    "⚠️ Aucune donnée",
                    f"Aucune vérification trouvée pour {date_str}",
                    parent=self
                )
                return

            export_dir = Path(f"exports/{date_str.replace('/', '-')}")
            export_dir.mkdir(parents=True, exist_ok=True)

            csv_file = export_dir / "remise_banque.csv"

            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';', lineterminator='\n')

                writer.writerow([
                    'Date',
                    'Numero piece',
                    'Designation',
                    'Debit',
                    'Credit'
                ])

                caisses_verif = verif_data.get('caisses_verif', {})
                compteur_piece = 1

                for num_caisse, caisse_data in caisses_verif.items():
                    num_piece = f"REM{compteur_piece:03d}"

                    total_billets = str(caisse_data.get('total_billets', 0)).replace('.', ',')
                    total_pieces = str(caisse_data.get('total_pieces', 0)).replace('.', ',')
                    total_especes = str(caisse_data.get('total_especes', 0)).replace('.', ',')

                    writer.writerow([
                        date_str,
                        num_piece,
                        f"Caisse {num_caisse} - BILLETS",
                        total_billets,
                        ''
                    ])

                    writer.writerow([
                        date_str,
                        num_piece,
                        f"Caisse {num_caisse} - PIECES",
                        total_pieces,
                        ''
                    ])

                    writer.writerow([
                        date_str,
                        num_piece,
                        f"Caisse {num_caisse} - TOTAL",
                        '',
                        total_especes
                    ])

                    compteur_piece += 1

            messagebox.showinfo(
                "✅ Export réussi",
                f"CSV sauvegardé:\n{csv_file}",
                parent=self
            )
            logger.info(f"CSV exporté: {csv_file}")

        except Exception as e:
            messagebox.showerror(
                "❌ Erreur export",
                f"Erreur: {str(e)}",
                parent=self
            )
            logger.error(f"Erreur export CSV : {e}")
