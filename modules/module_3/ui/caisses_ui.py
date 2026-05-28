"""
Module 3 UI - Gestion des caisses
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from pathlib import Path
import logging
import csv
import json

# ✅ IMPORTS RELATIFS (même dossier ou parent)
from ..auto_kiosque import generer_ligne_kiosque_auto
from ..stock import alimenter_depuis_caisse
from ..verification import (
    sauvegarder_verification,
    charger_verification,
    recalculer_totaux_verification,
    calculer_total_billets,
    calculer_total_pieces
)
from ..lecteur_caisse import (
    trouver_dossier_jour,
    lister_caisses,
    extraire_numero_caisse,
    lire_montants_caisse,
)

# ✅ IMPORTS MÊME NIVEAU (ui/)
from .detail_caisse import DetailCaissePopup
from .remise_ui import RemiseUI

logger = logging.getLogger(__name__)

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
    """Gestion des caisses du jour"""

    def __init__(self, parent, retour_callback):
        super().__init__(parent, bg="#1e1e2e")
        self.pack(fill="both", expand=True)
        self.retour = retour_callback
        self.date_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        self.caisses_data = {}
        self.caisses_data_original = {}
        self.donnees_corrigees = {}
        self.tree = None
        self.lbl_totaux = None
        self.lbl_statut = None

        # ✅ Génère la ligne auto au chargement
        try:
            generer_ligne_kiosque_auto()
        except Exception as e:
            logger.warning(f"⚠️ Kiosque auto: {e}")

        self._build_ui()
        self._charger_caisses()

    def _build_ui(self):
        """Construit l'interface"""
        self._build_header()
        self._build_barre_date()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=6)

        # ===== TAB CAISSES =====
        self.tab_caisses = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(self.tab_caisses, text="📋 Caisses du jour")
        self._build_tableau_caisses(self.tab_caisses)

        # ===== TAB REMISE =====
        tab_remise = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(tab_remise, text="🏦 Remises en banque")
        RemiseUI(tab_remise).pack(fill="both", expand=True)

    def _build_header(self):
        """En-tête avec bouton retour"""
        header = tk.Frame(self, bg="#181825", pady=10)
        header.pack(fill="x")

        tk.Button(
            header, text="← Retour",
            bg="#313244", fg="#cdd6f4",
            font=("Segoe UI", 10), relief="flat",
            padx=10, pady=4,
            command=self._retour
        ).pack(side="left", padx=12)

        tk.Label(
            header,
            text="💰 Gestion des Caisses",
            bg="#181825", fg="#cba6f7",
            font=("Segoe UI", 16, "bold")
        ).pack(side="left", padx=20)

    def _build_barre_date(self):
        """Barre de sélection de date et boutons"""
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
        ).pack(side="left", padx=4)

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

    def _charger_caisses(self):
        """Charge les caisses du jour"""
        date_str = self.date_var.get().strip()

        try:
            jour, mois, annee = map(int, date_str.split('/'))
            date_obj = date(annee, mois, jour)
        except Exception as e:
            messagebox.showerror("❌ Erreur date", f"Format invalide: {e}", parent=self)
            return

        try:
            dossier = trouver_dossier_jour(date_obj)
            if not dossier:
                self.lbl_statut.config(text="⚠️ Aucun dossier trouvé pour cette date")
                self.caisses_data = {}
                self._afficher_caisses()
                return

            fichiers = lister_caisses(dossier)
            self.caisses_data = {}
            self.caisses_data_original = {}

            for fichier in fichiers:
                try:
                    num = extraire_numero_caisse(fichier)
                    montants = lire_montants_caisse(fichier)
                    self.caisses_data[num] = montants
                    self.caisses_data_original[num] = montants.copy()
                except Exception as e:
                    logger.error(f"Erreur lecture {fichier}: {e}")

            self.lbl_statut.config(
                text=f"✅ {len(self.caisses_data)} caisse(s) chargée(s)"
            )
            self._afficher_caisses()

        except Exception as e:
            logger.error(f"Erreur chargement: {e}", exc_info=True)
            messagebox.showerror("❌ Erreur", f"Erreur: {e}", parent=self)

    def _afficher_caisses(self):
        """Affiche le tableau des caisses"""
        if not self.tree:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.caisses_data:
            self.lbl_totaux.config(text="Aucune caisse chargée")
            return

        totaux = {key: 0.0 for label, key in MODES}
        total_global = 0.0

        for num in sorted(self.caisses_data.keys()):
            data = self.caisses_data[num]
            valeurs = []
            ligne_total = 0.0

            for label, key in MODES:
                val = data.get(key, 0) or 0
                valeur_float = float(val) if val else 0.0
                valeurs.append(f"{valeur_float:.2f} €")
                totaux[key] += valeur_float
                ligne_total += valeur_float

            total_global += ligne_total

            tag = "pair" if int(num) % 2 == 0 else "impair"
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

    def _build_tableau_caisses(self, parent):
        """Construit le tableau des caisses"""
        colonnes = ["Caisse"] + [label for label, _ in MODES] + ["TOTAL"]

        frame_tree = tk.Frame(parent, bg="#1e1e2e")
        frame_tree.pack(fill="both", expand=True, padx=6, pady=6)

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical")
        scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal")

        self.tree = ttk.Treeview(
            frame_tree,
            columns=colonnes,
            height=15,
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        # ✅ COLONNES AVEC BONS ANCHORS (e = East = droite, w = West = gauche, center)
        self.tree.column("#0", width=0, stretch=False)
        self.tree.column("Caisse", anchor="center", width=100)
        for label, _ in MODES:
            self.tree.column(label, anchor="e", width=120)
        self.tree.column("TOTAL", anchor="e", width=120)  # ✅ "e" au lieu de "right"

        self.tree.heading("#0", text="", anchor="center")
        self.tree.heading("Caisse", text="Caisse", anchor="center")
        for label, _ in MODES:
            self.tree.heading(label, text=label, anchor="center")
        self.tree.heading("TOTAL", text="TOTAL", anchor="center")

        # ===== STYLE =====
        style = ttk.Style()
        style.configure(
            "Treeview",
            background="#313244",
            foreground="#cdd6f4",
            fieldbackground="#313244",
            font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading",
            background="#45475a",
            foreground="#89b4fa",
            font=("Segoe UI", 9, "bold")
        )
        style.map("Treeview", background=[("selected", "#45475a")])

        self.tree.tag_configure("pair", background="#2a2a3e")
        self.tree.tag_configure("impair", background="#313244")

        self.tree.pack(fill="both", expand=True, side="left")
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        self.tree.bind("<Double-1>", self._ouvrir_detail)

        # ===== LABEL DES TOTAUX =====
        self.lbl_totaux = tk.Label(
            parent, text="",
            bg="#1e1e2e", fg="#a6e3a1",
            font=("Segoe UI", 9, "bold"), wraplength=1200, justify="left"
        )
        self.lbl_totaux.pack(fill="x", padx=6, pady=6)

    def _ouvrir_detail(self, event):
        """Ouvre la popup de détail pour une caisse"""
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

    def _actualiser_caisse(self, num_caisse, donnees_modifiees):
        """Callback pour actualiser une caisse et alimenter le stock"""
        self.donnees_corrigees[num_caisse] = donnees_modifiees
        logger.info(f"Caisse {num_caisse} mise à jour : {donnees_modifiees}")

        # ✅ SAUVEGARDER LA VÉRIFICATION
        verif_data = {
            'caisses_verif': {
                f'Caisse {num_caisse}': donnees_modifiees
            }
        }
        sauvegarder_verification(self.date_var.get(), verif_data)

        # ✅ ALIMENTER LE STOCK
        try:
            alimenter_depuis_caisse(
                num_caisse,
                self.date_var.get(),
                donnees_modifiees
            )
            logger.info(f"✅ Stock alimenté depuis caisse {num_caisse}")
        except Exception as e:
            logger.error(f"❌ Erreur alimentation stock caisse {num_caisse}: {e}", exc_info=True)
            messagebox.showerror(
                "❌ Erreur Stock",
                f"Impossible d'alimenter le stock:\n{e}",
                parent=self
            )

        self._afficher_caisses()

    def _popup_kiosque(self):
        """Popup de saisie du kiosque photo"""
        popup = tk.Toplevel(self)
        popup.title("📷 Kiosque Photo")
        popup.configure(bg="#1e1e2e")
        popup.geometry("600x500")
        popup.resizable(False, True)

        date_str = self.date_var.get()

        tk.Label(
            popup, text="📷 Saisie Kiosque Photo",
            bg="#1e1e2e", fg="#cba6f7",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=15)

        # ===== COUPURES ESPÈCES =====
        frame_coupures = tk.LabelFrame(
            popup, text="Coupures",
            bg="#1e1e2e", fg="#cdd6f4",
            font=("Segoe UI", 10, "bold")
        )
        frame_coupures.pack(fill="x", padx=20, pady=10)

        coupures = [
            ("50€", 50), ("20€", 20), ("10€", 10),
            ("5€", 5), ("2€", 2), ("1€", 1),
            ("50¢", 0.5), ("20¢", 0.2), ("10¢", 0.1),
            ("5¢", 0.05), ("2¢", 0.02), ("1¢", 0.01)
        ]
        quantites = {}

        for i, (valeur_str, valeur_num) in enumerate(coupures):
            row = i // 3
            col = i % 3

            frame = tk.Frame(frame_coupures, bg="#1e1e2e")
            frame.grid(row=row, column=col, padx=8, pady=6, sticky="ew")

            tk.Label(
                frame, text=valeur_str,
                bg="#1e1e2e", fg="#cdd6f4",
                font=("Segoe UI", 9)
            ).pack(side="left", padx=5)

            var = tk.IntVar(value=0)
            quantites[valeur_num] = var

            tk.Spinbox(
                frame, from_=0, to=999,
                textvariable=var,
                width=6, bg="#313244", fg="#cdd6f4",
                font=("Segoe UI", 9)
            ).pack(side="left")

        def recalculer_total():
            total = 0.0
            for valeur_num, var in quantites.items():
                total += valeur_num * var.get()
            lbl_total.config(text=f"Total : {total:.2f} €")
            return total

        for var in quantites.values():
            var.trace("w", lambda *_: recalculer_total())

        lbl_total = tk.Label(
            frame_coupures, text="Total : 0.00 €",
            bg="#1e1e2e", fg="#a6e3a1",
            font=("Segoe UI", 11, "bold")
        )
        lbl_total.pack(pady=10)

        # ===== NOTES =====
        frame_notes = tk.LabelFrame(
            popup, text="Notes",
            bg="#1e1e2e", fg="#cdd6f4",
            font=("Segoe UI", 10, "bold")
        )
        frame_notes.pack(fill="x", padx=20, pady=10)

        notes_var = tk.StringVar()
        tk.Entry(
            frame_notes, textvariable=notes_var,
            font=("Segoe UI", 10),
            bg="#313244", fg="#cdd6f4", insertbackground="white"
        ).pack(fill="x", pady=5)

        # ===== BOUTONS =====
        frame_btn = tk.Frame(popup, bg="#1e1e2e")
        frame_btn.pack(fill="x", padx=20, pady=15)

        def valider():
            total = recalculer_total()

            if total == 0:
                messagebox.showwarning(
                    "⚠️ Montant requis",
                    "Entrez au moins une coupure",
                    parent=popup
                )
                return

            detail_especes = {}
            for valeur_str, valeur_num in coupures:
                qty = quantites[valeur_num].get()
                if qty > 0:
                    detail_especes[valeur_str] = qty

            entry = {
                "date": date_str,
                "type": "kiosque_photo",
                "montant": round(total, 2),
                "detail": detail_especes,
                "notes": notes_var.get(),
                "timestamp": datetime.now().isoformat()
            }

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

            logger.info(f"Kiosque sauvegardé: {json_file}")

            try:
                alimenter_depuis_caisse(
                    "KIOSQUE",
                    date_str,
                    {
                        "especes_bande": total,
                        "pieces_bande": 0,
                        "tous_modes": {"especes_bande": total}
                    }
                )
                logger.info("✅ Stock alimenté depuis kiosque photo")
            except Exception as e:
                logger.error(f"❌ Erreur alimentation stock kiosque: {e}")

            messagebox.showinfo(
                "✅ Succès",
                f"Kiosque sauvegardé: {total:.2f} €",
                parent=popup
            )
            popup.destroy()

        tk.Button(
            frame_btn, text="✅ Valider",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=15, pady=6,
            command=valider
        ).pack(side="left", padx=5)

        tk.Button(
            frame_btn, text="❌ Annuler",
            bg="#f38ba8", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=15, pady=6,
            command=popup.destroy
        ).pack(side="left", padx=5)

    def _sauvegarder_verification(self):
        """Sauvegarde TOUTES les caisses comme vérifiées"""
        date_str = self.date_var.get().strip()

        if not self.caisses_data:
            messagebox.showwarning(
                "⚠️ Aucune caisse",
                "Charger les caisses d'abord",
                parent=self
            )
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

            verif_data = {'caisses_verif': caisses_verif}
            sauvegarder_verification(date_str, verif_data)

            logger.info(f"✅ Vérifications sauvegardées : {caisses_verif}")
            messagebox.showinfo(
                "✅ Succès",
                f"{len(caisses_verif)} caisse(s) sauvegardée(s)",
                parent=self
            )

        except Exception as e:
            logger.error(f"Erreur sauvegarde : {e}")
            messagebox.showerror("❌ Erreur", f"Erreur : {e}", parent=self)

    def _exporter_csv_remise(self):
        """Exporte les caisses vérifiées en CSV pour la remise banque"""
        date_str = self.date_var.get().strip()

        recalculer_totaux_verification(date_str)
        verif_data = charger_verification(date_str)

        if not verif_data or not verif_data.get('caisses_verif'):
            messagebox.showwarning(
                "⚠️ Aucune verification",
                "Aucune verification trouvee pour cette date",
                parent=self
            )
            return

        export_dir = Path(f"exports/{date_str.replace('/', '-')}")
        export_dir.mkdir(parents=True, exist_ok=True)

        csv_file = export_dir / "remise_banque.csv"

        try:
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
                "✅ Export reussi",
                f"CSV sauvegarde: {csv_file}",
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

    def _retour(self):
        """Retourner à l'écran précédent"""
        self.destroy()
        if self.retour:
            self.retour()
