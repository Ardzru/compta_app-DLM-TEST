# ═══════════════════════════════════════════════════════════════════════════════
# FILE: modules/module_3/ui/caisses_ui.py — VERSION FINALE CORRIGÉE
# ═══════════════════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from pathlib import Path
from logging import getLogger
import csv
import json
from modules.module_3.handlers.stock_unified import alimenter_stock_complet
# ✅ IMPORTS MODULE_3 À LA RACINE
from modules.module_3 import lecteur_caisse, stock, verification
from modules.module_3.ui.detail_caisse import DetailCaissePopup
from modules.module_3.ui.remise_ui import RemiseUI

_log = getLogger("module_3.ui.caisses_ui")

MODES = [
    ("ESPÈCES", "especes_bande"),
    ("CB Sans contact", "cb_sans_contact"),
    ("CB Visa", "cb_visa"),
    ("DCC PLANET", "dcc_planet"),
    ("AMEX", "amex"),
    ("AMEX Sans contact", "amex_sans_contact"),
    ("ANCV Connect", "ancv_connect"),
    ("CHÈQUES VACANCES", "cheques_vac_bande"),
    ("BONS DE LIVRAISONS", "bons_livraisons"),
    ("CHÈQUES", "cheques_bande"),
    ("PAIEMENT WEB", "paiement_web"),
    ("VIREMENT", "virement"),
    ("CB VAD", "cb_vad"),
]

class AppCaisses(tk.Frame):
    """Gestion des caisses du jour."""

    def __init__(self, parent: tk.Widget, retour_callback) -> None:
        super().__init__(parent, bg="#1e1e2e")
        self.pack(fill="both", expand=True)

        self.retour = retour_callback
        self.date_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        self.caisses_data = {}
        self.caisses_data_original = {}
        self.donnees_corrigees = {}

        _log.debug("[MODULE3][UI] AppCaisses.__init__ appelé")
        self._build_ui()
        self._charger_caisses()

    # ═══════════════════════════════════════════════════════════════════════════
    # BUILD UI
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        """Construit l'interface complète."""
        self._build_header()
        self._build_barre_date()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=6)

        # Tab 1 : Caisses
        self.tab_caisses = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(self.tab_caisses, text="📋 Caisses du jour")
        self._build_tableau_caisses(self.tab_caisses)

        # Tab 2 : Remises
        tab_remise = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(tab_remise, text="🏦 Remises en banque")
        RemiseUI(tab_remise).pack(fill="both", expand=True)

    def _build_header(self) -> None:
        """Barre d'en-tête."""
        header = tk.Frame(self, bg="#181825", pady=10)
        header.pack(fill="x")

        tk.Button(
            header, text="← Retour",
            bg="#313244", fg="#cdd6f4",
            font=("Segoe UI", 10), relief="flat",
            padx=10, pady=4,
            command=self.retour
        ).pack(side="left", padx=12)

        tk.Label(
            header,
            text="💰 Gestion des Caisses",
            bg="#181825", fg="#cba6f7",
            font=("Segoe UI", 16, "bold")
        ).pack(side="left", padx=20)

    def _build_barre_date(self) -> None:
        """Barre de date et contrôles."""
        barre = tk.Frame(self, bg="#1e1e2e", pady=6)
        barre.pack(fill="x", padx=12)

        tk.Label(
            barre, text="Date (JJ/MM/AAAA) :",
            bg="#1e1e2e", fg="#cdd6f4",
            font=("Segoe UI", 10)
        ).pack(side="left")

        tk.Entry(
            barre, textvariable=self.date_var,
            width=14, bg="#313244", fg="#cdd6f4",
            insertbackground="white",
            font=("Segoe UI", 10)
        ).pack(side="left", padx=8)

        tk.Button(
            barre, text="🔄 Charger",
            bg="#89b4fa", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=10,
            command=self._charger_caisses
        ).pack(side="left")

        # ✅ BOUTON KIOSQUE PHOTO
        tk.Button(
            barre, text="📷 Kiosque Photo",
            bg="#f5c563", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=10,
            command=self._popup_kiosque
        ).pack(side="left", padx=4)

        tk.Button(
            barre, text="💾 Sauvegarder",
            bg="#f38ba8", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=10,
            command=self._sauvegarder_verification
        ).pack(side="left", padx=4)

        tk.Button(
            barre, text="📥 Exporter CSV",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=10,
            command=self._exporter_csv_remise
        ).pack(side="left", padx=4)

        self.lbl_statut = tk.Label(
            barre, text="",
            bg="#1e1e2e", fg="#a6e3a1",
            font=("Segoe UI", 10)
        )
        self.lbl_statut.pack(side="left", padx=16)

    def _build_tableau_caisses(self, parent: tk.Widget) -> None:
        """Crée le tableau des caisses."""
        colonnes = ["Caisse"] + [label for label, _ in MODES] + ["TOTAL"]

        frame_tree = tk.Frame(parent, bg="#1e1e2e")
        frame_tree.pack(fill="both", expand=True, padx=6, pady=6)

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical")
        scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal")

        self.tree = ttk.Treeview(
            frame_tree,
            columns=colonnes,
            height=20,
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )
        self.tree.column("#0", width=0, stretch=False)
        self.tree.heading("#0", text="")

        for col in colonnes:
            if col == "Caisse":
                w = 120
            elif col == "TOTAL":
                w = 100
            else:
                w = 90

            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center", minwidth=70)

        self.tree.tag_configure("pair", background="#313244")
        self.tree.tag_configure("ok", background="#2a2a3e")

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", self._ouvrir_detail)

        self.lbl_totaux = tk.Label(
            parent, text="",
            bg="#181825", fg="#f9e2af",
            font=("Segoe UI", 9),
            anchor="w", wraplength=1200
        )
        self.lbl_totaux.pack(fill="x", padx=8, pady=4)

    # ═══════════════════════════════════════════════════════════════════════════
    # CHARGEMENT / AFFICHAGE
    # ═══════════════════════════════════════════════════════════════════════════

    def _charger_caisses(self) -> None:
        """Charge les caisses pour la date saisie."""
        raw = self.date_var.get().strip()

        try:
            d = datetime.strptime(raw, "%d/%m/%Y").date()
        except ValueError:
            messagebox.showerror("Date invalide", "Format: JJ/MM/AAAA", parent=self)
            return

        _log.debug(f"[MODULE3][UI] _charger_caisses: {raw} → {d}")

        # ✅ CORRIGÉ
        dossier = lecteur_caisse.trouver_dossier_jour(d)

        if not dossier:
            self.lbl_statut.config(
                text=f"❌ Dossier introuvable pour {raw}",
                fg="#f38ba8"
            )
            self._vider_tableau()
            return

        # ✅ CORRIGÉ
        fichiers = lecteur_caisse.lister_caisses(dossier)

        if not fichiers:
            self.lbl_statut.config(text="❌ Aucune caisse trouvée", fg="#f38ba8")
            self._vider_tableau()
            return

        # Vider et réinitialiser
        self._vider_tableau()
        self.caisses_data = {}
        self.caisses_data_original = {}
        self.donnees_corrigees = {}

        # Charger chaque caisse
        for fich in fichiers:
            try:
                # ✅ CORRIGÉ
                num = lecteur_caisse.extraire_numero_caisse(fich)
                data = lecteur_caisse.lire_montants_caisse(fich)
                _log.debug(f"[MODULE3][UI] Caisse {num} chargée : {data}")

                self.caisses_data[num] = data.copy()
                self.caisses_data_original[num] = data.copy()
                self.donnees_corrigees[num] = {}

            except Exception as err:
                _log.error(f"[MODULE3][UI] Erreur lecture caisse {fich} : {err}")

        # Remplir le tableau
        self._remplir_tableau()

        self.lbl_statut.config(
            text=f"✅ {len(fichiers)} caisse(s) chargée(s)",
            fg="#a6e3a1"
        )

    def _vider_tableau(self) -> None:
        """Vide le tableau."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.lbl_totaux.config(text="")

    def _remplir_tableau(self) -> None:
        """Remplit le tableau avec les données."""
        self._vider_tableau()

        totaux = {k: 0.0 for _, k in MODES}
        total_global = 0.0

        for i, (num, d_original) in enumerate(sorted(self.caisses_data_original.items())):
            tag = "pair" if i % 2 == 0 else "ok"

            valeurs = []
            ligne_total = 0.0

            for _, key in MODES:
                v = d_original.get(key) or 0.0
                valeurs.append(f"{v:.2f} €" if v else "—")
                totaux[key] += v
                ligne_total += v

            total_global += ligne_total

            self.tree.insert(
                "", "end",
                iid=num,
                values=[f"Caisse {num}"] + valeurs + [f"{ligne_total:.2f} €"],
                tags=(tag,)
            )

        parties = []
        for label, key in MODES:
            if totaux[key] > 0:
                parties.append(f"{label} : {totaux[key]:.2f} €")

        self.lbl_totaux.config(
            text="TOTAUX  —  " + "   |   ".join(parties) +
                 f"   ‖   TOTAL : {total_global:.2f} €"
        )

    def _ouvrir_detail(self, event: tk.Event) -> None:
        """Ouvre le détail d'une caisse."""
        sel = self.tree.selection()
        if not sel:
            return

        num = sel[0]
        data = self.caisses_data_original.get(num, {}).copy()

        DetailCaissePopup(
            self,
            num,
            self.date_var.get(),
            data,
            self._actualiser_caisse
        )

    def _actualiser_caisse(self, num_caisse: str, donnees_modifiees: dict) -> None:
        """Actualise une caisse modifiée."""
        self.donnees_corrigees[num_caisse] = donnees_modifiees
        _log.info(f"[MODULE3][UI] Caisse {num_caisse} modifiée")

        # ✅ CORRIGÉ
        verification.sauvegarder_verification(
            self.date_var.get(),
            {
                'caisses_verif': {
                    f'Caisse {num_caisse}': donnees_modifiees
                }
            }
        )

        # Alimenter le stock
        if donnees_modifiees.get("validee"):
            try:
                # ✅ CORRIGÉ
                alimenter_stock_complet(
                    num_caisse,
                    self.date_var.get(),
                    donnees_modifiees
                )
                _log.info(f"[MODULE3][UI] Stock alimenté depuis caisse {num_caisse}")
            except Exception as err:
                _log.error(f"[MODULE3][UI] Erreur stock : {err}")

    # ═══════════════════════════════════════════════════════════════════════════
    # KIOSQUE PHOTO
    # ═══════════════════════════════════════════════════════════════════════════

    def _popup_kiosque(self) -> None:
        """Pop-up pour le kiosque photo."""
        popup = tk.Toplevel(self)
        popup.title("📷 Kiosque Photo")
        popup.geometry("700x750")
        popup.resizable(False, False)
        popup.grab_set()
        popup.transient(self)

        coupures = [
            ("500.00 €", 500),
            ("200.00 €", 200),
            ("100.00 €", 100),
            ("50.00 €", 50),
            ("20.00 €", 20),
            ("10.00 €", 10),
            ("5.00 €", 5),
            ("2.00 €", 2),
            ("1.00 €", 1),
            ("0.50 €", 0.50),
            ("0.20 €", 0.20),
            ("0.10 €", 0.10),
            ("0.05 €", 0.05),
            ("0.02 €", 0.02),
            ("0.01 €", 0.01),
        ]

        # ── HEADER ──
        header = tk.Frame(popup, bg="#313244", pady=12)
        header.pack(fill='x')

        tk.Label(
            header, text="💰 ESPÈCES",
            bg="#313244", fg="#89b4fa",
            font=('Segoe UI', 13, 'bold')
        ).pack()

        # ── TABLEAU COUPURES ──
        frame_tree = tk.Frame(popup, bg="#1e1e2e")
        frame_tree.pack(fill='both', expand=True, padx=15, pady=10)

        frame_header = tk.Frame(frame_tree, bg="#313244")
        frame_header.pack(fill='x', pady=(0, 5))

        tk.Label(frame_header, text="Valeur", bg="#313244", fg="#cdd6f4",
                 font=('Segoe UI', 9, 'bold'), width=20, anchor='w', padx=5).pack(side='left')
        tk.Label(frame_header, text="Quantité", bg="#313244", fg="#cdd6f4",
                 font=('Segoe UI', 9, 'bold'), width=15, anchor='center').pack(side='left')
        tk.Label(frame_header, text="Montant", bg="#313244", fg="#cdd6f4",
                 font=('Segoe UI', 9, 'bold'), width=15, anchor='center').pack(side='left')

        canvas = tk.Canvas(frame_tree, bg="#1e1e2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame_tree, orient='vertical', command=canvas.yview)
        scrollable = tk.Frame(canvas, bg="#1e1e2e")

        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        quantites = {}
        montants = {}

        for idx, (valeur_str, valeur_num) in enumerate(coupures):
            frame_row = tk.Frame(scrollable, bg="#1e1e2e" if idx % 2 == 0 else "#151520")
            frame_row.pack(fill='x', pady=2)

            tk.Label(frame_row, text=valeur_str, bg=frame_row['bg'], fg="#89b4fa",
                     font=('Segoe UI', 10), width=20, anchor='w', padx=5).pack(side='left')

            qty_var = tk.StringVar(value="0")
            quantites[valeur_num] = qty_var

            entry_qty = tk.Entry(frame_row, textvariable=qty_var, width=12,
                                 font=('Segoe UI', 11), bg="#313244", fg="#cdd6f4",
                                 insertbackground="white", justify='center')
            entry_qty.pack(side='left', padx=5)

            lbl_montant = tk.Label(frame_row, text="= 0.00 €", bg=frame_row['bg'],
                                   fg="#a6e3a1", font=('Segoe UI', 10), width=15, anchor='center')
            lbl_montant.pack(side='left', padx=5)
            montants[valeur_num] = lbl_montant

            def creer_callback(val_num):
                def on_change(*args):
                    try:
                        qty = float(qty_var.get()) if qty_var.get() else 0
                        montant = qty * val_num
                        montants[val_num].config(text=f"= {montant:.2f} €")
                        recalculer_total()
                    except ValueError:
                        pass

                return on_change

            qty_var.trace('w', creer_callback(valeur_num))

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # ── TOTAUX ──
        frame_totaux = tk.Frame(popup, bg="#181825", pady=12)
        frame_totaux.pack(fill='x', padx=15, pady=10)

        lbl_total = tk.Label(
            frame_totaux, text="Total saisi: 0.00 €",
            bg="#181825", fg="#a6e3a1",
            font=('Segoe UI', 12, 'bold')
        )
        lbl_total.pack()

        lbl_diff = tk.Label(
            frame_totaux, text="Diff: +0.00 €",
            bg="#181825", fg="#f9e2af",
            font=('Segoe UI', 11)
        )
        lbl_diff.pack()

        def recalculer_total() -> float:
            """Recalcule le total et la différence."""
            total = 0.0
            for valeur_num in quantites.keys():
                try:
                    qty = float(quantites[valeur_num].get()) if quantites[valeur_num].get() else 0
                    total += qty * valeur_num
                except ValueError:
                    pass

            lbl_total.config(text=f"Total saisi: {total:.2f} €")
            lbl_diff.config(text=f"Diff: +{total:.2f} €")
            return total

        # ── NOTES ──
        frame_notes = tk.Frame(popup, bg="#1e1e2e")
        frame_notes.pack(fill='x', padx=15, pady=5)

        tk.Label(frame_notes, text="Notes:", bg="#1e1e2e", fg="#cdd6f4",
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w')

        notes_var = tk.StringVar()
        tk.Entry(frame_notes, textvariable=notes_var, font=('Segoe UI', 10),
                 bg="#313244", fg="#cdd6f4", insertbackground="white").pack(fill='x', pady=5)

        # ── BOUTONS ──
        frame_btn = tk.Frame(popup, bg="#1e1e2e")
        frame_btn.pack(fill='x', padx=15, pady=15)

        def valider() -> None:
            """Valide et sauvegarde."""
            total = recalculer_total()

            if total == 0:
                messagebox.showwarning("⚠️ Montant requis",
                                       "Entrez au moins une coupure", parent=popup)
                return

            detail_parts = []
            detail_especes = {}

            for valeur_str, valeur_num in coupures:
                try:
                    qty = float(quantites[valeur_num].get()) if quantites[valeur_num].get() else 0
                    if qty > 0:
                        detail_parts.append(f"{int(qty)}x{valeur_str}")
                        detail_especes[str(valeur_num)] = {
                            "quantite": int(qty),
                            "montant": qty * valeur_num
                        }
                except ValueError:
                    pass

            detail = " + ".join(detail_parts)
            notes = notes_var.get().strip()
            date_str = self.date_var.get()

            kiosque_entry = {
                'montant': total,
                'detail': detail,
                'notes': notes,
                'heure': datetime.now().strftime('%H:%M:%S'),
                'date': date_str
            }

            self._sauvegarder_kiosque(date_str, kiosque_entry)

            try:
                # ✅ CORRIGÉ
                stock.alimenter_depuis_caisse(
                    'kiosque',
                    date_str,
                    {
                        'detail_especes': detail_especes,
                        'detail_cheques_vac_coupures': {},
                        'detail_cheques': [],
                        'ancv_connect': 0.0
                    }
                )
                _log.info(f"[MODULE3][UI] Stock alimenté depuis kiosque")
            except Exception as err:
                _log.error(f"[MODULE3][UI] Erreur stock kiosque : {err}")
                messagebox.showerror("❌ Erreur", f"Erreur stock: {err}", parent=popup)
                return

            popup.destroy()
            messagebox.showinfo(
                "✅ Kiosque Photo",
                f"Montant: {total:.2f}€\n✓ Stock alimenté",
                parent=self
            )

        tk.Button(frame_btn, text="✅ Valider", command=valider,
                  bg="#a6e3a1", fg="#1e1e2e", font=('Segoe UI', 11, 'bold'),
                  relief='flat', padx=20, pady=8, width=20).pack(side='left', padx=5)

        tk.Button(frame_btn, text="❌ Annuler", command=popup.destroy,
                  bg="#f38ba8", fg="#1e1e2e", font=('Segoe UI', 11, 'bold'),
                  relief='flat', padx=20, pady=8, width=20).pack(side='left', padx=5)

    def _sauvegarder_kiosque(self, date_str: str, entry: dict) -> None:
        """Sauvegarde l'entrée kiosque en JSON."""
        json_dir = Path("data/kiosque")
        json_dir.mkdir(parents=True, exist_ok=True)

        date_fmt = date_str.replace('/', '-')
        json_file = json_dir / f"kiosque_{date_fmt}.json"

        data = []
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = []

        data.append(entry)

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        _log.info(f"[MODULE3][UI] Kiosque sauvegardé : {json_file}")

    # ═══════════════════════════════════════════════════════════════════════════
    # VERIFICATION ET EXPORT
    # ═══════════════════════════════════════════════════════════════════════════

    def _sauvegarder_verification(self) -> None:
        """Sauvegarde toutes les caisses comme vérifiées."""
        date_str = self.date_var.get().strip()

        if not self.caisses_data:
            messagebox.showwarning("⚠️ Aucune caisse", "Charger les caisses d'abord", parent=self)
            return

        try:
            caisses_verif = {}

            for num_caisse, data in self.caisses_data.items():
                if num_caisse in self.donnees_corrigees:
                    caisse_data = self.donnees_corrigees[num_caisse]
                else:
                    caisse_data = data.copy()

                especes = caisse_data.get('especes_bande', 0) or 0
                pieces = caisse_data.get('pieces_bande', 0) or 0

                caisses_verif[f'Caisse {num_caisse}'] = {
                    'total_billets': float(especes),
                    'total_pieces': float(pieces),
                    'total_especes': float(especes) + float(pieces),
                    'validee': True,
                    'date': date_str,
                    'tous_modes': caisse_data
                }

            # ✅ CORRIGÉ
            verification.sauvegarder_verification(date_str, {'caisses_verif': caisses_verif})

            _log.info(f"[MODULE3][UI] Vérifications sauvegardées")
            messagebox.showinfo(
                "✅ Succès",
                f"{len(caisses_verif)} caisse(s) sauvegardée(s)",
                parent=self
            )

        except Exception as err:
            _log.error(f"[MODULE3][UI] Erreur sauvegarde : {err}")
            messagebox.showerror("❌ Erreur", f"Erreur : {err}", parent=self)

    def _exporter_csv_remise(self) -> None:
        """Exporte les caisses en CSV pour la remise banque."""
        date_str = self.date_var.get().strip()

        # ✅ CORRIGÉ
        verif_data = verification.charger_verification(date_str)

        if not verif_data or not verif_data.get('caisses_verif'):
            messagebox.showwarning(
                "⚠️ Aucune vérification",
                "Aucune vérification trouvée pour cette date",
                parent=self
            )
            return

        export_dir = Path(f"exports/{date_str.replace('/', '-')}")
        export_dir.mkdir(parents=True, exist_ok=True)

        csv_file = export_dir / "remise_banque.csv"

        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';', lineterminator='\n')

                writer.writerow(['Date', 'Numero piece', 'Designation', 'Debit', 'Credit'])

                caisses_verif = verif_data.get('caisses_verif', {})
                compteur_piece = 1

                for num_caisse, caisse_data in caisses_verif.items():
                    num_piece = f"REM{compteur_piece:03d}"

                    total_billets = str(caisse_data.get('total_billets', 0)).replace('.', ',')
                    total_pieces = str(caisse_data.get('total_pieces', 0)).replace('.', ',')
                    total_especes = str(caisse_data.get('total_especes', 0)).replace('.', ',')

                    writer.writerow([date_str, num_piece, f"Caisse {num_caisse} - BILLETS", total_billets, ''])
                    writer.writerow([date_str, num_piece, f"Caisse {num_caisse} - PIECES", total_pieces, ''])
                    writer.writerow([date_str, num_piece, f"Caisse {num_caisse} - TOTAL", '', total_especes])

                    compteur_piece += 1

            messagebox.showinfo(
                "✅ Export réussi",
                f"CSV sauvegardé: {csv_file}",
                parent=self
            )
            _log.info(f"[MODULE3][UI] CSV exporté : {csv_file}")

        except Exception as err:
            messagebox.showerror("❌ Erreur export", f"Erreur: {str(err)}", parent=self)
            _log.error(f"[MODULE3][UI] Erreur export CSV : {err}")


__all__ = ["AppCaisses"]
