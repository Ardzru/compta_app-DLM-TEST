import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

BILLETS = [500, 200, 100, 50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01]

COUPURES_VAC = [50, 25, 20, 10]

TOUS_LES_MODES = [
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


class DetailCaissePopup(tk.Toplevel):
    def __init__(self, parent, num_caisse: str, date_str: str,
                 data: dict, callback_update):
        super().__init__(parent)
        self.title(f"Caisse {num_caisse} — {date_str}")
        self.geometry("1600x900")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")

        self.num_caisse = num_caisse
        self.date_str = date_str
        self.data_original = data.copy()
        self.callback_update = callback_update

        self.statut_validation = "NON_VALIDEE"

        self._attendu = {}
        self._saisi = {}
        self._entries_saisie = {}
        self._entries_especes = {}
        self._verif_labels = {}
        self.lbl_status = None
        self.lbl_total_esp = None

        self.cache_dir = Path("cache_caisses")
        self.cache_dir.mkdir(exist_ok=True, parents=True)

        safe_date = re.sub(r'[/\\:]', '-', date_str)
        self.cache_file = self.cache_dir / f"caisse_{num_caisse}_{safe_date}.json"

        logger.debug(f"Cache file: {self.cache_file}")

        self._load_or_create_cache()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────
    # CACHE
    # ─────────────────────────────────────────────

    def _load_or_create_cache(self):
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                self._attendu = cached.get("attendu", self.data_original)
                self._saisi = cached.get("saisi", {})
                self.statut_validation = cached.get("statut", "NON_VALIDEE")
                logger.info(f"✅ Cache chargé depuis {self.cache_file}")
            else:
                self._attendu = self.data_original.copy()
                self._saisi = {
                    key: self._attendu.get(key, 0.0)
                    for _, key in TOUS_LES_MODES
                }
                self._save_cache()
        except Exception as e:
            logger.error(f"❌ Erreur load cache: {e}")
            self._attendu = self.data_original.copy()
            self._saisi = {
                key: self._attendu.get(key, 0.0)
                for _, key in TOUS_LES_MODES
            }

    def _save_cache(self):
        try:
            cache_data = {
                "attendu": self._attendu,
                "saisi": self._saisi,
                "statut": self.statut_validation,
                "timestamp": datetime.now().isoformat()
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"💾 Cache sauvegardé : {self.cache_file}")
        except Exception as e:
            logger.error(f"❌ Erreur save cache: {e}")

    # ─────────────────────────────────────────────
    # UI PRINCIPALE
    # ─────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#313244",
                        foreground="#cdd6f4", padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", "#45475a")])

        notebook = ttk.Notebook(self, style="TNotebook")
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self._build_tab_saisie(notebook)
        self._build_tab_verification(notebook)
        self._build_footer()

    def _build_header(self):
        frame_header = tk.Frame(self, bg="#313244", height=60)
        frame_header.pack(fill="x")
        frame_header.pack_propagate(False)

        tk.Label(
            frame_header,
            text=f"Caisse {self.num_caisse} — {self.date_str}",
            bg="#313244", fg="#cdd6f4", font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=15, pady=15)

        color = "#a6e3a1" if self.statut_validation == "VALIDEE" else "#f38ba8"
        self.lbl_status = tk.Label(
            frame_header,
            text=f"Status: {self.statut_validation}",
            bg="#313244", fg=color, font=("Segoe UI", 12, "bold")
        )
        self.lbl_status.pack(side="right", padx=15, pady=15)

    # ─────────────────────────────────────────────
    # ONGLET SAISIE — 3 COLONNES
    # ─────────────────────────────────────────────

    def _build_tab_saisie(self, notebook):
        frame_saisie = tk.Frame(notebook, bg="#1e1e2e")
        notebook.add(frame_saisie, text="📝 Saisie")

        canvas = tk.Canvas(frame_saisie, bg="#1e1e2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame_saisie, orient="vertical",
                                  command=canvas.yview)
        content = tk.Frame(canvas, bg="#1e1e2e")

        content.bind("<Configure>",
                     lambda e: canvas.configure(
                         scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        col1 = tk.Frame(content, bg="#1e1e2e")
        col1.pack(side="left", fill="both", expand=True, padx=5, anchor="n")

        col2 = tk.Frame(content, bg="#1e1e2e")
        col2.pack(side="left", fill="both", expand=True, padx=5, anchor="n")

        col3 = tk.Frame(content, bg="#1e1e2e")
        col3.pack(side="left", fill="both", expand=True, padx=5, anchor="n")

        self._build_especes_section(col1)
        self._build_cheques_vac_section(col2)
        self._build_ancv_connect_section(col2)
        self._build_cheques_section(col2)
        self._build_autres_modes_section(col3)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(
                            int(-1 * (e.delta / 120)), "units"))

    # ─────────────────────────────────────────────
    # SECTIONS SAISIE
    # ─────────────────────────────────────────────

    def _build_especes_section(self, parent):
        frame_esp = tk.LabelFrame(
            parent, text="💰 ESPÈCES", bg="#2a2a3e", fg="#cdd6f4",
            font=("Segoe UI", 11, "bold"), padx=10, pady=10
        )
        frame_esp.pack(fill="x", padx=5, pady=10)

        attendu_esp = self._attendu.get("especes_bande", 0.0)
        tk.Label(
            frame_esp, text=f"Attendu: {attendu_esp:.2f} €",
            bg="#2a2a3e", fg="#89b4fa", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=5, pady=(5, 2))

        hdr = tk.Frame(frame_esp, bg="#2a2a3e")
        hdr.pack(fill="x", padx=5)
        for txt, w in [("Valeur", 10), ("Quantité", 8), ("Montant", 12)]:
            tk.Label(hdr, text=txt, bg="#2a2a3e", fg="#6c7086",
                     width=w, anchor="w", font=("Segoe UI", 8, "italic")
                     ).pack(side="left", padx=3)

        detail_esp = self._attendu.get("detail_especes", {})

        for billet in BILLETS:
            frame_b = tk.Frame(frame_esp, bg="#2a2a3e")
            frame_b.pack(fill="x", padx=5, pady=2)

            tk.Label(frame_b, text=f"{billet:.2f} €",
                     bg="#2a2a3e", fg="#cdd6f4",
                     width=10, anchor="w", font=("Segoe UI", 9)
                     ).pack(side="left", padx=3)

            detail_key = str(billet)
            qty_stored = 0
            if detail_key in detail_esp:
                qty_stored = detail_esp[detail_key].get("quantite", 0)
            elif billet in detail_esp:
                qty_stored = detail_esp[billet].get("quantite", 0)

            entry_qty = tk.Entry(frame_b, width=8, font=("Segoe UI", 9))
            entry_qty.insert(0, str(qty_stored))
            entry_qty.pack(side="left", padx=3)

            lbl_montant = tk.Label(
                frame_b, text=f"= {qty_stored * billet:.2f} €",
                bg="#2a2a3e", fg="#a6e3a1",
                width=12, anchor="w", font=("Segoe UI", 9)
            )
            lbl_montant.pack(side="left", padx=3)

            self._entries_especes[billet] = (entry_qty, lbl_montant)

            def _upd_esp(event=None, b=billet):
                try:
                    q = int(self._entries_especes[b][0].get())
                    self._entries_especes[b][1].config(
                        text=f"= {q * b:.2f} €")
                    self._update_total_especes()
                except Exception:
                    pass

            entry_qty.bind("<KeyRelease>", _upd_esp)
            entry_qty.bind("<FocusOut>", _upd_esp)

        total_init = sum(
            int(e.get()) * b
            for b, (e, _) in self._entries_especes.items()
        )
        diff_init = total_init - attendu_esp
        color_init = "#a6e3a1" if abs(diff_init) < 0.01 else "#f38ba8"

        self.lbl_total_esp = tk.Label(
            frame_esp, text=f"Total saisi: {total_init:.2f} €",
            bg="#2a2a3e", fg="#fab387", font=("Segoe UI", 11, "bold")
        )
        self.lbl_total_esp.pack(anchor="w", padx=5, pady=(8, 2))

        self.lbl_diff_esp = tk.Label(
            frame_esp, text=f"Diff: {diff_init:+.2f} €",
            bg="#2a2a3e", fg=color_init, font=("Segoe UI", 10, "bold")
        )
        self.lbl_diff_esp.pack(anchor="w", padx=5, pady=(0, 5))

        self._update_total_especes()

    def _update_total_especes(self):
        total = 0.0
        detail = {}
        for billet, (entry_qty, _) in self._entries_especes.items():
            try:
                q = int(entry_qty.get())
                total += q * billet
                detail[str(billet)] = {"quantite": q, "montant": round(q * billet, 2)}
            except Exception:
                pass

        if self.lbl_total_esp:
            self.lbl_total_esp.config(text=f"Total saisi: {total:.2f} €")

        attendu = self._attendu.get("especes_bande", 0.0)
        diff = total - attendu
        color = "#a6e3a1" if abs(diff) < 0.01 else "#f38ba8"
        self.lbl_diff_esp.config(text=f"Diff: {diff:+.2f} €", fg=color)

        self._saisi["especes_bande"] = total
        self._saisi["detail_especes"] = detail
        self._attendu["detail_especes"] = detail
        self._refresh_verif_diff("especes_bande", total)
        self._save_cache()

    def _build_cheques_vac_section(self, parent):
        frame = tk.LabelFrame(
            parent, text="🎫 CHÈQUES VACANCES", bg="#2a2a3e", fg="#cdd6f4",
            font=("Segoe UI", 11, "bold"), padx=10, pady=10
        )
        frame.pack(fill="x", padx=5, pady=10)

        attendu = self._attendu.get("cheques_vac_bande", 0.0)
        tk.Label(
            frame, text=f"Attendu : {attendu:.2f} €",
            bg="#2a2a3e", fg="#89b4fa", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=5, pady=(5, 2))

        hdr = tk.Frame(frame, bg="#2a2a3e")
        hdr.pack(fill="x", padx=5)
        for txt, w in [("Coupure", 10), ("Quantité", 8), ("Montant", 12)]:
            tk.Label(hdr, text=txt, bg="#2a2a3e", fg="#6c7086",
                     width=w, anchor="w", font=("Segoe UI", 8, "italic")
                     ).pack(side="left", padx=3)

        self._entries_cheques_vac = {}
        detail_vac = self._attendu.get("detail_cheques_vac_coupures", {})

        for coupure in COUPURES_VAC:
            frame_c = tk.Frame(frame, bg="#2a2a3e")
            frame_c.pack(fill="x", padx=5, pady=2)

            tk.Label(frame_c, text=f"{coupure:.0f} €",
                     bg="#2a2a3e", fg="#cdd6f4",
                     width=10, anchor="w", font=("Segoe UI", 9)
                     ).pack(side="left", padx=3)

            qty_stored = detail_vac.get(str(coupure), {}).get("quantite", 0)

            entry_qty = tk.Entry(frame_c, width=8, font=("Segoe UI", 9))
            entry_qty.insert(0, str(qty_stored))
            entry_qty.pack(side="left", padx=3)

            lbl_montant = tk.Label(
                frame_c, text=f"= {qty_stored * coupure:.2f} €",
                bg="#2a2a3e", fg="#a6e3a1",
                width=12, anchor="w", font=("Segoe UI", 9)
            )
            lbl_montant.pack(side="left", padx=3)

            self._entries_cheques_vac[coupure] = (entry_qty, lbl_montant)

            def _upd(event=None, c=coupure):
                try:
                    q = int(self._entries_cheques_vac[c][0].get())
                    self._entries_cheques_vac[c][1].config(
                        text=f"= {q * c:.2f} €")
                    self._update_total_cheques_vac()
                except Exception:
                    pass

            entry_qty.bind("<KeyRelease>", _upd)
            entry_qty.bind("<FocusOut>", _upd)

        total_init = sum(
            int(e.get()) * c
            for c, (e, _) in self._entries_cheques_vac.items()
        )
        diff_init = total_init - attendu
        color_init = "#a6e3a1" if abs(diff_init) < 0.01 else "#f38ba8"

        self.lbl_total_vac = tk.Label(
            frame, text=f"Total saisi: {total_init:.2f} €",
            bg="#2a2a3e", fg="#fab387", font=("Segoe UI", 11, "bold")
        )
        self.lbl_total_vac.pack(anchor="w", padx=5, pady=(8, 2))

        self.lbl_diff_vac = tk.Label(
            frame, text=f"Diff: {diff_init:+.2f} €",
            bg="#2a2a3e", fg=color_init, font=("Segoe UI", 10, "bold")
        )
        self.lbl_diff_vac.pack(anchor="w", padx=5, pady=(0, 5))

        self._update_total_cheques_vac()

    def _update_total_cheques_vac(self):
        total = 0.0
        detail = {}
        for coupure, (entry, _) in self._entries_cheques_vac.items():
            try:
                q = int(entry.get())
                total += q * coupure
                detail[str(coupure)] = {"quantite": q, "montant": q * coupure}
            except Exception:
                pass

        attendu = self._attendu.get("cheques_vac_bande", 0.0)
        diff = total - attendu
        color = "#a6e3a1" if abs(diff) < 0.01 else "#f38ba8"

        self.lbl_total_vac.config(text=f"Total saisi: {total:.2f} €")
        self.lbl_diff_vac.config(text=f"Diff: {diff:+.2f} €", fg=color)

        # ✅ TRIPLE SAVE
        self._attendu["detail_cheques_vac_coupures"] = detail
        self._saisi["cheques_vac_bande"] = total
        self._saisi["detail_cheques_vac_coupures"] = detail

        self._refresh_verif_diff("cheques_vac_bande", total)
        self._save_cache()

    def _build_ancv_connect_section(self, parent):
        frame = tk.LabelFrame(
            parent, text="🎟️ ANCV CONNECT", bg="#2a2a3e", fg="#cdd6f4",
            font=("Segoe UI", 11, "bold"), padx=10, pady=10
        )
        frame.pack(fill="x", padx=5, pady=10)

        attendu = self._attendu.get("ancv_connect", 0.0)
        tk.Label(frame, text=f"Attendu : {attendu:.2f} €",
                 bg="#2a2a3e", fg="#89b4fa",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=5, pady=(5, 2))

        cols_frame = tk.Frame(frame, bg="#2a2a3e")
        cols_frame.pack(fill="x", padx=5)
        for txt, w in [("Montant (€)", 12)]:
            tk.Label(cols_frame, text=txt, bg="#2a2a3e", fg="#6c7086",
                     width=w, anchor="w", font=("Segoe UI", 8, "italic")
                     ).pack(side="left", padx=3)

        self._ancv_rows_frame = tk.Frame(frame, bg="#2a2a3e")
        self._ancv_rows_frame.pack(fill="x", padx=5)
        self._ancv_entries = []

        lignes_ancv = self._saisi.get("detail_ancv_connect", [])
        if not lignes_ancv:
            lignes_ancv = []

        for ligne in lignes_ancv:
            self._add_ancv_row(ligne.get("montant", 0.0))

        self.lbl_total_ancv = tk.Label(
            frame, text="Total : 0.00 €",
            bg="#2a2a3e", fg="#fab387", font=("Segoe UI", 11, "bold"))
        self.lbl_total_ancv.pack(anchor="w", padx=5, pady=(5, 2))

        self.lbl_diff_ancv = tk.Label(
            frame, text="Diff : +0.00 €",
            bg="#2a2a3e", fg="#a6e3a1", font=("Segoe UI", 10, "bold"))
        self.lbl_diff_ancv.pack(anchor="w", padx=5, pady=(0, 5))

        tk.Button(frame, text="➕ Ajouter", bg="#45475a", fg="#cdd6f4",
                  font=("Segoe UI", 9), relief="flat",
                  command=lambda: self._add_ancv_row()
                  ).pack(anchor="w", padx=5, pady=5)

        self._update_total_ancv()

    def _add_ancv_row(self, montant=0.0):
        row = tk.Frame(self._ancv_rows_frame, bg="#2a2a3e")
        row.pack(fill="x", pady=1)

        entry_m = tk.Entry(row, width=12, font=("Segoe UI", 9))
        entry_m.insert(0, f"{montant:.2f}" if montant else "")
        entry_m.pack(side="left", padx=3)

        def suppr():
            self._ancv_entries.remove(entry_m)
            row.destroy()
            self._update_total_ancv()

        tk.Button(row, text="🗑️", bg="#2a2a3e", fg="#f38ba8",
                  font=("Segoe UI", 9), relief="flat",
                  command=suppr).pack(side="left", padx=2)

        self._ancv_entries.append(entry_m)
        entry_m.bind("<KeyRelease>", lambda e: self._update_total_ancv())
        entry_m.bind("<FocusOut>", lambda e: self._update_total_ancv())

    def _update_total_ancv(self):
        total = 0.0
        detail = []
        for entry in self._ancv_entries:
            try:
                val = float(entry.get().replace(",", "."))
                total += val
                detail.append({"montant": val})
            except Exception:
                pass

        attendu = self._attendu.get("ancv_connect", 0.0)
        diff = total - attendu
        color = "#a6e3a1" if abs(diff) < 0.01 else "#f38ba8"

        self.lbl_total_ancv.config(text=f"Total : {total:.2f} €")
        self.lbl_diff_ancv.config(text=f"Diff : {diff:+.2f} €", fg=color)

        self._saisi["ancv_connect"] = total
        self._saisi["detail_ancv_connect"] = detail
        self._refresh_verif_diff("ancv_connect", total)
        self._save_cache()

    def _build_cheques_section(self, parent):
        frame = tk.LabelFrame(
            parent, text="✓ CHÈQUES", bg="#2a2a3e", fg="#cdd6f4",
            font=("Segoe UI", 11, "bold"), padx=10, pady=10
        )
        frame.pack(fill="x", padx=5, pady=10)

        attendu = self._attendu.get("cheques_bande", 0.0)
        tk.Label(frame, text=f"Attendu : {attendu:.2f} €",
                 bg="#2a2a3e", fg="#89b4fa",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=5, pady=(5, 2))

        hdr = tk.Frame(frame, bg="#2a2a3e")
        hdr.pack(fill="x", padx=5)
        for txt, w in [("N° Chèque", 14), ("Montant (€)", 12)]:
            tk.Label(hdr, text=txt, bg="#2a2a3e", fg="#6c7086",
                     width=w, anchor="w", font=("Segoe UI", 8, "italic")
                     ).pack(side="left", padx=3)

        self._cheques_rows_frame = tk.Frame(frame, bg="#2a2a3e")
        self._cheques_rows_frame.pack(fill="x", padx=5)
        self._cheques_entries = []

        lignes = self._saisi.get("detail_cheques", [])
        for ligne in lignes:
            self._add_cheque_row(ligne.get("numero", ""), ligne.get("montant", 0.0))

        self.lbl_total_cheques = tk.Label(
            frame, text="Total : 0.00 €",
            bg="#2a2a3e", fg="#fab387", font=("Segoe UI", 11, "bold"))
        self.lbl_total_cheques.pack(anchor="w", padx=5, pady=(5, 2))

        self.lbl_diff_cheques = tk.Label(
            frame, text="Diff : +0.00 €",
            bg="#2a2a3e", fg="#a6e3a1", font=("Segoe UI", 10, "bold"))
        self.lbl_diff_cheques.pack(anchor="w", padx=5, pady=(0, 5))

        tk.Button(frame, text="➕ Ajouter", bg="#45475a", fg="#cdd6f4",
                  font=("Segoe UI", 9), relief="flat",
                  command=lambda: self._add_cheque_row()
                  ).pack(anchor="w", padx=5, pady=5)

        self._update_total_cheques()

    def _add_cheque_row(self, numero="", montant=0.0):
        row = tk.Frame(self._cheques_rows_frame, bg="#2a2a3e")
        row.pack(fill="x", pady=1)

        entry_n = tk.Entry(row, width=14, font=("Segoe UI", 9))
        entry_n.insert(0, str(numero))
        entry_n.pack(side="left", padx=3)

        entry_m = tk.Entry(row, width=12, font=("Segoe UI", 9))
        entry_m.insert(0, f"{montant:.2f}" if montant else "")
        entry_m.pack(side="left", padx=3)

        def suppr():
            self._cheques_entries.remove((entry_n, entry_m))
            row.destroy()
            self._update_total_cheques()

        tk.Button(row, text="🗑️", bg="#2a2a3e", fg="#f38ba8",
                  font=("Segoe UI", 9), relief="flat",
                  command=suppr).pack(side="left", padx=2)

        self._cheques_entries.append((entry_n, entry_m))
        entry_m.bind("<KeyRelease>", lambda e: self._update_total_cheques())
        entry_m.bind("<FocusOut>", lambda e: self._update_total_cheques())

    def _update_total_cheques(self):
        total = 0.0
        detail = []
        for entry_n, entry_m in self._cheques_entries:
            try:
                val = float(entry_m.get().replace(",", "."))
                total += val
                detail.append({"numero": entry_n.get(), "montant": val})
            except Exception:
                pass

        attendu = self._attendu.get("cheques_bande", 0.0)
        diff = total - attendu
        color = "#a6e3a1" if abs(diff) < 0.01 else "#f38ba8"

        self.lbl_total_cheques.config(text=f"Total : {total:.2f} €")
        self.lbl_diff_cheques.config(text=f"Diff : {diff:+.2f} €", fg=color)

        self._saisi["cheques_bande"] = total
        self._saisi["detail_cheques"] = detail
        self._refresh_verif_diff("cheques_bande", total)
        self._save_cache()

    def _build_autres_modes_section(self, parent):
        frame_autres = tk.LabelFrame(
            parent, text="💳 AUTRES MODES", bg="#2a2a3e", fg="#cdd6f4",
            font=("Segoe UI", 11, "bold"), padx=10, pady=10
        )
        frame_autres.pack(fill="x", padx=5, pady=10)

        modes_exclus = {
            "especes_bande", "cheques_vac_bande",
            "ancv_connect", "cheques_bande"
        }

        for label, key in TOUS_LES_MODES:
            if key in modes_exclus:
                continue

            frame_mode = tk.Frame(frame_autres, bg="#2a2a3e")
            frame_mode.pack(fill="x", padx=5, pady=4)

            attendu = self._attendu.get(key, 0.0)
            tk.Label(frame_mode, text=f"{label}",
                     bg="#2a2a3e", fg="#cdd6f4",
                     width=20, anchor="w", font=("Segoe UI", 9)
                     ).pack(side="left", padx=5)

            tk.Label(frame_mode, text=f"{attendu:.2f} €",
                     bg="#2a2a3e", fg="#89b4fa",
                     width=10, anchor="w", font=("Segoe UI", 9)
                     ).pack(side="left", padx=5)

            saisi = self._saisi.get(key, attendu)
            entry = tk.Entry(frame_mode, width=10, font=("Segoe UI", 9))
            entry.insert(0, f"{saisi:.2f}")
            entry.pack(side="left", padx=5)

            diff = saisi - attendu
            color = "#a6e3a1" if abs(diff) < 0.01 else "#f38ba8"
            lbl_diff = tk.Label(frame_mode, text=f"Diff: {diff:+.2f} €",
                                bg="#2a2a3e", fg=color, font=("Segoe UI", 9)
                                )
            lbl_diff.pack(side="left", padx=5)

            self._entries_saisie[key] = entry

            def _upd(event=None, k=key, e=entry, a=attendu, ld=lbl_diff):
                try:
                    val = float(e.get().replace(",", "."))
                    self._saisi[k] = val
                    d = val - a
                    c = "#a6e3a1" if abs(d) < 0.01 else "#f38ba8"
                    ld.config(text=f"Diff: {d:+.2f} €", fg=c)
                    self._refresh_verif_diff(k, val)
                    self._save_cache()
                except Exception:
                    pass

            entry.bind("<KeyRelease>", _upd)
            entry.bind("<FocusOut>", _upd)

    # ─────────────────────────────────────────────
    # ONGLET VÉRIFICATION — LECTURE SEULE
    # ─────────────────────────────────────────────

    def _build_tab_verification(self, notebook):
        frame_verif = tk.Frame(notebook, bg="#1e1e2e")
        notebook.add(frame_verif, text="✓ Vérification")

        hdr = tk.Frame(frame_verif, bg="#313244")
        hdr.pack(fill="x", padx=10, pady=(10, 0))
        for txt, w in [("Mode", 25), ("Attendu", 15),
                       ("Saisi", 15), ("Différence", 15)]:
            tk.Label(hdr, text=txt, bg="#313244", fg="#89b4fa",
                     width=w, anchor="w",
                     font=("Segoe UI", 10, "bold")
                     ).pack(side="left", padx=5, pady=5)

        canvas = tk.Canvas(frame_verif, bg="#1e1e2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame_verif, orient="vertical",
                                  command=canvas.yview)
        content = tk.Frame(canvas, bg="#1e1e2e")

        content.bind("<Configure>",
                     lambda e: canvas.configure(
                         scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        for label, key in TOUS_LES_MODES:
            self._build_verif_row(content, label, key)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y")

        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(
                            int(-1 * (e.delta / 120)), "units"))

    def _build_verif_row(self, parent, label, key):
        """Ligne lecture seule dans la vérification"""
        attendu = self._attendu.get(key, 0.0)
        saisi = self._saisi.get(key, 0.0)
        diff = saisi - attendu
        color = "#a6e3a1" if abs(diff) < 0.01 else "#f38ba8"

        bg = "#2a2a3e" if list(self._verif_labels).count(key) == 0 else "#252535"

        frame = tk.Frame(parent, bg=bg, relief="flat", bd=0)
        frame.pack(fill="x", padx=5, pady=2)

        tk.Label(frame, text=label, bg=bg, fg="#cdd6f4",
                 width=25, anchor="w", font=("Segoe UI", 10)
                 ).pack(side="left", padx=10, pady=6)

        tk.Label(frame, text=f"{attendu:.2f} €", bg=bg, fg="#89b4fa",
                 width=15, anchor="w", font=("Segoe UI", 10)
                 ).pack(side="left", padx=5)

        lbl_saisi = tk.Label(frame, text=f"{saisi:.2f} €", bg=bg,
                             fg="#fab387", width=15, anchor="w",
                             font=("Segoe UI", 10, "bold"))
        lbl_saisi.pack(side="left", padx=5)

        lbl_diff = tk.Label(frame, text=f"{diff:+.2f} €", bg=bg,
                            fg=color, width=15, anchor="w",
                            font=("Segoe UI", 10, "bold"))
        lbl_diff.pack(side="left", padx=5)

        self._verif_labels[key] = (lbl_diff, lbl_saisi, attendu)

    def _refresh_verif_diff(self, key, saisi):
        """Rafraîchir diff ET valeur saisie dans la vérification"""
        if key in self._verif_labels:
            lbl_diff, lbl_saisi, attendu = self._verif_labels[key]
            diff = saisi - attendu
            color = "#a6e3a1" if abs(diff) < 0.01 else "#f38ba8"
            lbl_diff.config(text=f"{diff:+.2f} €", fg=color)
            lbl_saisi.config(text=f"{saisi:.2f} €")

    # ─────────────────────────────────────────────
    # FOOTER
    # ─────────────────────────────────────────────

    def _build_footer(self):
        frame_btn = tk.Frame(self, bg="#313244", height=60)
        frame_btn.pack(fill="x", side="bottom")
        frame_btn.pack_propagate(False)

        tk.Button(
            frame_btn, text="✅ VALIDÉE",
            bg="#a6e3a1", fg="#000", font=("Segoe UI", 11, "bold"),
            padx=20, pady=8, relief="raised", bd=2,
            command=self._valider
        ).pack(side="left", padx=10, pady=10)

        tk.Button(
            frame_btn, text="⚠️ NON VALIDÉE",
            bg="#f38ba8", fg="#000", font=("Segoe UI", 11, "bold"),
            padx=20, pady=8, relief="raised", bd=2,
            command=self._non_valider
        ).pack(side="left", padx=5, pady=10)

        tk.Button(
            frame_btn, text="❌ QUITTER",
            bg="#6c7086", fg="#fff", font=("Segoe UI", 11, "bold"),
            padx=20, pady=8, relief="raised", bd=2,
            command=self._on_close
        ).pack(side="right", padx=10, pady=10)

    # ─────────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────────

    def _valider(self):
        """Valider SANS fermer la fenêtre"""
        self.statut_validation = "VALIDEE"

        data_finale = self._saisi.copy()
        data_finale["validee"] = True
        data_finale["timestamp_validation"] = datetime.now().isoformat()

        self._save_cache()

        # ✅ SAUVEGARDE DANS LE FICHIER DE VÉRIFICATION GLOBAL
        from core.verification import sauvegarder_verification

        try:
            verif_data = {
                'caisses_verif': {
                    f'Caisse {self.num_caisse}': data_finale
                }
            }
            sauvegarder_verification(self.date_str, verif_data)
            logger.info(f"✅ Vérification sauvegardée pour caisse {self.num_caisse}")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde vérification: {e}")

        logger.info(f"✅ Caisse {self.num_caisse} VALIDÉE")

        try:
            self.callback_update(self.num_caisse, data_finale)
            self.lbl_status.config(
                text="Status: ✅ VALIDEE — Sauvegardée ✓", fg="#a6e3a1")
            self.after(3000, lambda: self.lbl_status.config(
                text="Status: ✅ VALIDEE", fg="#a6e3a1"))
        except Exception as e:
            logger.error(f"❌ Erreur callback: {e}")
            self.lbl_status.config(
                text=f"Status: ❌ ERREUR — {e}", fg="#f38ba8")

        self.lift()
        self.focus_force()

    def _non_valider(self):
        self.statut_validation = "NON_VALIDEE"
        self.lbl_status.config(text="Status: ⚠️ NON VALIDÉE", fg="#f38ba8")
        self._save_cache()
        logger.info(f"⚠️ Caisse {self.num_caisse} NON VALIDÉE")

    def _on_close(self):
        self._save_cache()
        logger.info(f"📋 Caisse {self.num_caisse} fermée et sauvegardée")
        self.destroy()
