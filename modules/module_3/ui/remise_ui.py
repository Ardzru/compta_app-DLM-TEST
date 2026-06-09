# ═══════════════════════════════════════════════════════════════════════════════
# FILE: modules/module_3/ui/remise_ui.py — VERSION FINALE COMPLÈTE
# ═══════════════════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, messagebox
import json
from datetime import datetime
from logging import getLogger

from core.utils.montant import format_montant
from modules.module_3 import remises, stock

_log = getLogger("module_3.ui.remise_ui")

TYPE_LABELS = {
    "especes": ("💶 Espèces", "#a6e3a1"),
    "cheques_vac": ("🏖️ Chèques Vacances", "#f9e2af"),
    "cheques": ("📄 Chèques", "#cba6f7"),
}

COUPURES_ESPECES = ["500", "200", "100", "50", "20", "10", "5", "2", "1",
                    "0.5", "0.2", "0.1", "0.05", "0.02", "0.01"]
COUPURES_CHEQ_VAC = ["50", "25", "20", "10"]
FONT_MONO = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")


# ─── HELPERS ───────────────────────────────────────────────────────
def _parse_detail(detail: dict | str) -> dict:
    """Convertit le detail en dict."""
    if isinstance(detail, dict):
        return detail
    if isinstance(detail, str):
        try:
            return json.loads(detail)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def _qte(info: dict | int) -> int:
    """Extrait la quantité de plusieurs formats."""
    try:
        if isinstance(info, dict):
            return int(info.get("quantite", 0))
        return int(info)
    except (ValueError, TypeError):
        return 0


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════
class RemiseUI(tk.Frame):
    """UI pour la gestion des remises en banque."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg="#1e1e2e")
        _log.debug("[MODULE3][UI] RemiseUI.__init__ appelé")
        self._build()

    def _build(self) -> None:
        """Construit les 4 onglets."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)  # type: ignore

        tab1 = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(tab1, text="📦 Stock")
        self._build_stock(tab1)

        tab2 = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(tab2, text="⏳ En attente")
        self._build_attente(tab2)

        tab3 = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(tab3, text="📋 Historique")
        self._build_historique(tab3)

        tab4 = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(tab4, text="🔄 Echanges")
        self._build_echanges_tab(tab4)

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 1: STOCK
    # ═══════════════════════════════════════════════════════════════
    def _build_stock(self, parent: tk.Widget) -> None:
        """Affiche le stock actuel avec boutons de remise."""
        parent.configure(bg="#1e1e2e")

        # ── En-tête ──
        header = tk.Frame(parent, bg="#1e1e2e")
        header.pack(fill="x", padx=14, pady=(10, 4))  # type: ignore
        tk.Label(header, text="📦 Stock actuel",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=FONT_BOLD).pack(side="left")  # type: ignore

        tk.Button(header, text="🔄 Rafraichir",
                  bg="#313244", fg="#cdd6f4",
                  font=FONT_MONO, relief="flat", padx=10, pady=4,
                  command=self._charger_stock).pack(side="right", padx=4)  # type: ignore

        tk.Button(header, text="🗑️ Reset (test)",
                  bg="#f38ba8", fg="#1e1e2e",
                  font=FONT_MONO, relief="flat", padx=10, pady=4,
                  command=self._reset_stock).pack(side="right", padx=4)  # type: ignore

        # ── Maj ──
        self._lbl_maj = tk.Label(parent, text="",
                                 bg="#1e1e2e", fg="#6c7086",
                                 font=("Segoe UI", 8, "italic"))
        self._lbl_maj.pack(anchor="w", padx=14, pady=(0, 4))

        # ── Scroll ──
        canvas = tk.Canvas(parent, bg="#1e1e2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical",
                                  command=canvas.yview)
        self._frame_stock = tk.Frame(canvas, bg="#1e1e2e")
        self._frame_stock.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self._frame_stock, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")  # type: ignore
        canvas.pack(fill="both", expand=True, padx=10)  # type: ignore

        self._charger_stock()

    def _charger_stock(self) -> None:
        """Charge et affiche le stock."""
        _log.debug("[MODULE3][UI] _charger_stock appelé")
        for widget in self._frame_stock.winfo_children():
            widget.destroy()

        stock_data = stock.get_stock()
        maj = stock_data.get("derniere_maj") or "jamais"
        self._lbl_maj.config(text=f"Dernière mise à jour : {maj}")

        # ── ESPECES ──
        especes_raw = stock_data.get("especes", {})
        especes_norm = {c: _qte(especes_raw.get(c, 0))
                        for c in COUPURES_ESPECES}
        billets_esp = {c: q for c, q in especes_norm.items() if q > 0}
        total_esp = sum(float(c) * q for c, q in billets_esp.items())

        self._afficher_carte_stock(
            type_remise="especes",
            billets=especes_norm if billets_esp else None,
            total=total_esp
        )

        # ── CHEQUES VACANCES ──
        cheq_vac_raw = stock_data.get("cheques_vac", {})
        cheq_vac_norm = {c: _qte(cheq_vac_raw.get(c, 0))
                         for c in COUPURES_CHEQ_VAC}
        billets_vac = {c: q for c, q in cheq_vac_norm.items() if q > 0}
        total_vac = sum(float(c) * q for c, q in billets_vac.items())

        self._afficher_carte_stock(
            type_remise="cheques_vac",
            billets=cheq_vac_norm,
            total=total_vac
        )

        # ── CHEQUES ──
        cheques = stock_data.get("cheques", [])
        total_cheq = sum(ch.get("montant", 0.0) for ch in cheques)

        self._afficher_carte_stock(
            type_remise="cheques",
            cheques=cheques,
            total=total_cheq
        )

    def _afficher_carte_stock(
        self,
        type_remise: str,
        billets: dict[str, int] | None = None,
        cheques: list | None = None,
        total: float = 0.0
    ) -> None:
        """Affiche une carte pour un type de remise."""
        label, color = TYPE_LABELS.get(type_remise, (type_remise, "#cdd6f4"))

        card = tk.Frame(self._frame_stock, bg="#2a2a3e",
                        relief="flat", highlightthickness=0)
        card.pack(fill="x", pady=8)  # type: ignore

        # ── En-tête ──
        row = tk.Frame(card, bg="#2a2a3e")
        row.pack(fill="x")  # type: ignore

        tk.Label(row, text=f"Total : {format_montant(total)}",
                 bg="#2a2a3e", fg=color,
                 font=FONT_BOLD).pack(side="left", padx=12, pady=8)  # type: ignore

        tk.Button(
            row,
            text="🏦 Remettre en banque",
            bg="#313244", fg=color,
            font=FONT_MONO, relief="flat", padx=8, pady=2,
            command=lambda t=type_remise: self._dialog_remise(t)
        ).pack(side="right", padx=12, pady=8)  # type: ignore

        # ── Détail billets ──
        if billets is not None:
            liste = (COUPURES_ESPECES if type_remise == "especes"
                     else COUPURES_CHEQ_VAC)

            has_detail = any(billets.get(c, 0) > 0 for c in liste)

            if has_detail:
                tk.Label(card, text="Détail :",
                         bg="#2a2a3e", fg="#6c7086",
                         font=("Segoe UI", 8, "italic")).pack(
                    anchor="w", padx=12, pady=(4, 0))

                any_shown = False
                for val_c in liste:
                    qte = billets.get(val_c, 0)
                    if type_remise == "especes" and qte == 0:
                        continue
                    any_shown = True
                    montant = float(val_c) * qte
                    couleur = "#cdd6f4" if qte > 0 else "#45475a"
                    tk.Label(
                        card,
                        text=f"  {val_c} € × {qte} = {format_montant(montant)}",
                        bg="#2a2a3e", fg=couleur,
                        font=FONT_MONO
                    ).pack(anchor="w", padx=12)

                if not any_shown:
                    tk.Label(card, text="— aucun billet en stock —",
                             bg="#2a2a3e", fg="#6c7086",
                             font=("Segoe UI", 8, "italic")).pack(
                        anchor="w", padx=12, pady=4)

        # ── Détail cheques ──
        elif cheques is not None and cheques:
            tk.Label(card, text="Détail :",
                     bg="#2a2a3e", fg="#6c7086",
                     font=("Segoe UI", 8, "italic")).pack(
                anchor="w", padx=12, pady=(4, 0))

            for cheque in cheques:
                num = cheque.get("num", "—")
                mont = cheque.get("montant", 0.0)
                caisse = cheque.get("caisse", "")
                txt = f"  N° {num} → {format_montant(mont)}"
                if caisse:
                    txt += f" (caisse {caisse})"
                tk.Label(card, text=txt,
                         bg="#2a2a3e", fg="#cdd6f4",
                         font=FONT_MONO).pack(anchor="w", padx=12)

    def _reset_stock(self) -> None:
        """Réinitialise le stock."""
        _log.debug("[MODULE3][UI] _reset_stock appelé")
        if messagebox.askyesno(
                "⚠️ Reset stock",
                "Remettre le stock à zéro ?\n"
                "À utiliser uniquement pour les tests.",
                icon="warning"
        ):
            stock.reset_stock()
            self._charger_stock()

    # ═══════════════════════════════════════════════════════════════
    # DIALOGUES REMISE
    # ═══════════════════════════════════════════════════════════════
    def _dialog_remise(self, type_remise: str) -> None:
        """Dispatcher vers le bon dialogue."""
        _log.debug(f"[MODULE3][UI] _dialog_remise: {type_remise}")
        stock_data = stock.get_stock()

        if type_remise == "cheques":
            self._dialog_cheques(stock_data.get("cheques", []))
        else:
            self._dialog_coupures(type_remise, stock_data)

    def _dialog_coupures(self, type_remise: str, stock_data: dict) -> None:
        """Dialogue pour Especes et Cheques Vacances."""
        _log.debug(f"[MODULE3][UI] _dialog_coupures: {type_remise}")

        label, color = TYPE_LABELS[type_remise]
        liste_coupures = (COUPURES_ESPECES if type_remise == "especes"
                          else COUPURES_CHEQ_VAC)

        raw = stock_data.get(type_remise, {})
        billets_norm = {c: _qte(raw.get(c, 0)) for c in liste_coupures}

        if type_remise == "especes":
            coupures_affichees = [(c, billets_norm[c])
                                  for c in liste_coupures
                                  if billets_norm[c] > 0]
        else:
            coupures_affichees = [(c, billets_norm[c])
                                  for c in liste_coupures]

        nb_lignes = len(coupures_affichees)
        hauteur = max(400, min(120 + nb_lignes * 44 + 200, 680))

        win = tk.Toplevel(self)
        win.title(f"Remise — {label}")
        win.configure(bg="#1e1e2e")
        win.resizable(False, True)
        win.grab_set()
        win.geometry(f"480x{hauteur}")
        x = self.winfo_toplevel().winfo_x() + 150
        y = self.winfo_toplevel().winfo_y() + 60
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text=f"🏦 Remise — {label}",
                 bg="#1e1e2e", fg=color,
                 font=FONT_TITLE).pack(pady=(14, 4))

        # ── Date ──
        frame_dt = tk.Frame(win, bg="#1e1e2e")
        frame_dt.pack(pady=4)
        tk.Label(frame_dt, text="Date :",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))  # type: ignore
        var_date = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        tk.Entry(frame_dt, textvariable=var_date,
                 bg="#313244", fg="#cdd6f4",
                 font=("Segoe UI", 10), width=12, justify="center",
                 insertbackground="#cdd6f4", relief="flat").pack(side="left")  # type: ignore

        tk.Label(win, text="Sélectionnez les coupures à remettre :",
                 bg="#1e1e2e", fg="#6c7086",
                 font=("Segoe UI", 9, "italic")).pack(pady=(6, 2))

        # ── Tableau ──
        frame_canvas = tk.Frame(win, bg="#2a2a3e", relief="groove", bd=1)
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=4)  # type: ignore

        canvas_t = tk.Canvas(frame_canvas, bg="#2a2a3e",
                             highlightthickness=0)
        vsb = ttk.Scrollbar(frame_canvas, orient="vertical",
                            command=canvas_t.yview)
        frame_table = tk.Frame(canvas_t, bg="#2a2a3e")
        frame_table.bind(
            "<Configure>",
            lambda e: canvas_t.configure(scrollregion=canvas_t.bbox("all"))
        )
        canvas_t.create_window((0, 0), window=frame_table, anchor="nw")
        canvas_t.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")  # type: ignore
        canvas_t.pack(fill="both", expand=True)  # type: ignore

        def _handle_mwheel(event: tk.Event) -> None:
            canvas_t.yview_scroll(int(-1 * (event.delta / 120)), "units")  # type: ignore

        canvas_t.bind_all("<MouseWheel>", _handle_mwheel)

        vars_qte: dict[str, tk.IntVar] = {}
        lbl_sts: dict[str, tk.Label] = {}
        lbl_total_var = tk.StringVar(value="0.00 €")

        def _update_total(*_: tk.Event) -> None:  # type: ignore
            total = 0.0
            for coupure_key, var_qte_val in vars_qte.items():
                qte = var_qte_val.get()
                montant = float(coupure_key) * qte
                lbl_sts[coupure_key].config(text=format_montant(montant))
                total += montant
            lbl_total_var.set(format_montant(total))

        for row_idx, (coupure, qte_stock) in enumerate(coupures_affichees):
            tk.Label(frame_table, text=f"{coupure} €",
                     bg="#2a2a3e", fg="#cdd6f4",
                     font=("Segoe UI", 9, "bold")).grid(
                row=row_idx, column=0, sticky="w", padx=6, pady=3)

            tk.Label(frame_table, text=f"× {qte_stock}",
                     bg="#2a2a3e", fg="#6c7086",
                     font=FONT_MONO, width=8).grid(
                row=row_idx, column=1, padx=6, pady=3)

            var = tk.IntVar(value=0)
            vars_qte[coupure] = var

            tk.Spinbox(
                frame_table, from_=0, to=qte_stock, textvariable=var,
                bg="#313244", fg="#cdd6f4",
                font=FONT_MONO, width=6,
                command=_update_total
            ).grid(row=row_idx, column=2, padx=6, pady=3)

            lbl_st = tk.Label(frame_table, text="0.00 €",
                              bg="#2a2a3e", fg="#6c7086",
                              font=FONT_MONO, width=12, anchor="e")
            lbl_st.grid(row=row_idx, column=3, padx=6, pady=3)
            lbl_sts[coupure] = lbl_st

        # ── Total ──
        frame_tot = tk.Frame(win, bg="#1e1e2e")
        frame_tot.pack(pady=8)
        tk.Label(frame_tot, text="Total :",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 8))  # type: ignore
        tk.Label(frame_tot, textvariable=lbl_total_var,
                 bg="#1e1e2e", fg=color,
                 font=("Segoe UI", 11, "bold")).pack(side="left")  # type: ignore

        lbl_err = tk.Label(win, text="", bg="#1e1e2e", fg="#f38ba8",
                           font=FONT_MONO)
        lbl_err.pack()

        # ── BUTTON VALIDER ────────────────────────────────────────
        btn_f = tk.Frame(win, bg="#1e1e2e")
        btn_f.pack(side="bottom", pady=8)

        def _valider() -> None:
            _log.debug(f"[MODULE3][UI] Validation remise {type_remise}")
            btn_valider.config(state="disabled", text="⏳ Traitement...")
            win.update()

            try:
                try:
                    date_obj = datetime.strptime(
                        var_date.get().strip(), "%d/%m/%Y")
                    date_str = date_obj.strftime("%Y-%m-%d")
                except ValueError as err:
                    _log.error(f"Erreur date: {err}")
                    lbl_err.config(
                        text="⚠️ Date invalide (JJ/MM/AAAA)")
                    btn_valider.config(state="normal", text="✅ Valider")
                    return

                # ✅ CREER LE DETAIL CORRECT
                detail: dict[str, dict | float] = {
                    "billets": {},
                    "total": 0.0
                }

                for coupure, var_q in vars_qte.items():
                    qte = var_q.get()
                    if qte > 0:
                        montant = float(coupure) * qte
                        detail["billets"][coupure] = {
                            "quantite": qte,
                            "montant": montant
                        }
                        detail["total"] = float(detail["total"]) + montant

                total = float(detail["total"])

                if total <= 0:
                    _log.warning("Remise vide")
                    lbl_err.config(text="⚠️ Selectionnez au moins un billet")
                    btn_valider.config(state="normal", text="✅ Valider")
                    return

                if not messagebox.askyesno(
                        "Confirmer la remise",
                        f"{label}\nTotal : {format_montant(total)}\n\nCreer la remise ?",
                        parent=win
                ):
                    _log.debug("Utilisateur a annule")
                    btn_valider.config(state="normal", text="✅ Valider")
                    return

                _log.info(f"Creation remise {type_remise}: {format_montant(total)}")

                # ✅ CREER LA REMISE
                remises.ajouter_remise(
                    date_caisse=date_str,
                    num_caisse="MANUEL",
                    type_remise=type_remise,
                    detail=detail,
                )
                _log.info("Remise creee en BDD")

                # ✅ DECRÉMENTER LE STOCK
                stock.retirer_remise(type_remise, detail)
                _log.info("Stock deduit")

                canvas_t.unbind_all("<MouseWheel>")
                win.destroy()

                messagebox.showinfo(
                    "✅ Remise cree",
                    f"{label}\n{format_montant(total)}\nStock mis à jour."
                )
                self.notebook.select(1)
                self._charger_attente()
                self._charger_stock()

            except (IOError, ValueError, KeyError) as err:
                _log.error(f"Erreur remise: {err}", exc_info=True)
                lbl_err.config(text=f"❌ Erreur: {str(err)}")
                btn_valider.config(state="normal", text="✅ Valider")

        btn_valider = tk.Button(
            btn_f, text="✅ Valider",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=16, pady=6,
            command=_valider
        )
        btn_valider.pack(side="left", padx=8)  # type: ignore

        tk.Button(
            btn_f, text="❌ Annuler",
            bg="#f38ba8", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=16, pady=6,
            command=lambda: (canvas_t.unbind_all("<MouseWheel>"), win.destroy())
        ).pack(side="left", padx=8)  # type: ignore

        win.bind("<Escape>", lambda e: (canvas_t.unbind_all("<MouseWheel>"), win.destroy()))

    def _dialog_cheques(self, cheques: list) -> None:
        """Dialogue pour les cheques."""
        _log.debug("[MODULE3][UI] _dialog_cheques appelé")

        label, color = TYPE_LABELS["cheques"]

        win = tk.Toplevel(self)
        win.title(f"Remise — {label}")
        win.configure(bg="#1e1e2e")
        win.resizable(False, True)
        win.grab_set()
        win.geometry("480x520")
        x = self.winfo_toplevel().winfo_x() + 150
        y = self.winfo_toplevel().winfo_y() + 60
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text=f"🏦 Remise — {label}",
                 bg="#1e1e2e", fg=color,
                 font=FONT_TITLE).pack(pady=(14, 4))

        # ── Date ──
        frame_dt = tk.Frame(win, bg="#1e1e2e")
        frame_dt.pack(pady=4)
        tk.Label(frame_dt, text="Date :",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))  # type: ignore
        var_date = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        tk.Entry(frame_dt, textvariable=var_date,
                 bg="#313244", fg="#cdd6f4",
                 font=("Segoe UI", 10), width=12, justify="center",
                 insertbackground="#cdd6f4", relief="flat").pack(side="left")  # type: ignore

        tk.Label(win, text="Selectionnez les cheques à remettre :",
                 bg="#1e1e2e", fg="#6c7086",
                 font=("Segoe UI", 9, "italic")).pack(pady=(6, 2))

        # ── Tableau cheques ──
        frame_canvas = tk.Frame(win, bg="#2a2a3e", relief="groove", bd=1)
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=4)  # type: ignore

        canvas_c = tk.Canvas(frame_canvas, bg="#2a2a3e",
                             highlightthickness=0)
        vsb = ttk.Scrollbar(frame_canvas, orient="vertical",
                            command=canvas_c.yview)
        frame_table = tk.Frame(canvas_c, bg="#2a2a3e")
        frame_table.bind(
            "<Configure>",
            lambda e: canvas_c.configure(scrollregion=canvas_c.bbox("all"))
        )
        canvas_c.create_window((0, 0), window=frame_table, anchor="nw")
        canvas_c.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")  # type: ignore
        canvas_c.pack(fill="both", expand=True)  # type: ignore

        def _handle_mwheel_c(event: tk.Event) -> None:
            canvas_c.yview_scroll(int(-1 * (event.delta / 120)), "units")  # type: ignore

        canvas_c.bind_all("<MouseWheel>", _handle_mwheel_c)

        vars_sel: dict[str, tk.BooleanVar] = {}
        lbl_total_var = tk.StringVar(value="0.00 €")

        def _update_total_c(*_: tk.Event) -> None:  # type: ignore
            total = 0.0
            for idx_cheq, var_s in vars_sel.items():
                if var_s.get():
                    cheq_idx = int(idx_cheq)
                    cheq = cheques[cheq_idx]
                    total += cheq.get("montant", 0.0)
            lbl_total_var.set(format_montant(total))

        for idx_cheq, cheque in enumerate(cheques):
            num = cheque.get("num", "?")
            montant = cheque.get("montant", 0.0)
            caisse = cheque.get("caisse", "")

            row = tk.Frame(frame_table, bg="#2a2a3e")
            row.pack(fill="x", padx=8, pady=3)  # type: ignore

            var = tk.BooleanVar(value=False)
            vars_sel[str(idx_cheq)] = var

            chk = tk.Checkbutton(
                row, text=f"N° {num} → {format_montant(montant)}",
                variable=var,
                bg="#2a2a3e", fg="#cdd6f4",
                font=FONT_MONO,
                command=_update_total_c,
                activebackground="#313244",
                selectcolor="#2a2a3e"
            )
            chk.pack(side="left", anchor="w")  # type: ignore
            if caisse:
                tk.Label(row, text=f"(caisse {caisse})",
                         bg="#2a2a3e", fg="#6c7086",
                         font=("Segoe UI", 8, "italic")).pack(side="right", padx=4)  # type: ignore

        # ── Total ──
        frame_tot = tk.Frame(win, bg="#1e1e2e")
        frame_tot.pack(pady=8)
        tk.Label(frame_tot, text="Total :",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 8))  # type: ignore
        tk.Label(frame_tot, textvariable=lbl_total_var,
                 bg="#1e1e2e", fg=color,
                 font=("Segoe UI", 11, "bold")).pack(side="left")  # type: ignore

        lbl_err = tk.Label(win, text="", bg="#1e1e2e", fg="#f38ba8",
                           font=FONT_MONO)
        lbl_err.pack()

        # ── BUTTON VALIDER ────────────────────────────────────────
        btn_f = tk.Frame(win, bg="#1e1e2e")
        btn_f.pack(side="bottom", pady=8)

        def _valider_cheq() -> None:
            _log.debug("[MODULE3][UI] Validation remise cheques")
            btn_valider_cheq.config(state="disabled", text="⏳ Traitement...")
            win.update()

            try:
                try:
                    date_obj = datetime.strptime(
                        var_date.get().strip(), "%d/%m/%Y")
                    date_str = date_obj.strftime("%Y-%m-%d")
                except ValueError as err:
                    _log.error(f"Erreur date: {err}")
                    lbl_err.config(
                        text="⚠️ Date invalide (JJ/MM/AAAA)")
                    btn_valider_cheq.config(state="normal", text="✅ Valider")
                    return

                # Récupérer les chèques sélectionnés
                selectionnes = []
                total = 0.0
                for idx_s, var_sel in vars_sel.items():
                    if var_sel.get():
                        cheq_idx = int(idx_s)
                        cheq = cheques[cheq_idx]
                        selectionnes.append(cheq)
                        total += cheque.get("montant", 0.0)

                if not selectionnes:
                    _log.warning("Aucun cheque selectionne")
                    lbl_err.config(text="⚠️ Selectionnez au moins un cheque")
                    btn_valider_cheq.config(state="normal", text="✅ Valider")
                    return

                if not messagebox.askyesno(
                        "Confirmer la remise",
                        f"Cheques — {format_montant(total)}\n"
                        f"{len(selectionnes)} cheque(s)\n\n"
                        f"Creer la remise ?",
                        parent=win
                ):
                    _log.debug("Utilisateur a annule")
                    btn_valider_cheq.config(state="normal", text="✅ Valider")
                    return

                detail: dict[str, float | list] = {
                    "total": round(total, 2),
                    "cheques": selectionnes
                }

                _log.info("Creation remise cheques en BDD")
                remises.ajouter_remise(
                    date_caisse=date_str,
                    num_caisse="MANUEL",
                    type_remise="cheques",
                    detail=detail,
                )
                _log.info("Remise creee")

                _log.info("Deduction stock cheques")
                stock.retirer_remise("cheques", detail)
                _log.info("Stock deduit")

                canvas_c.unbind_all("<MouseWheel>")
                win.destroy()

                messagebox.showinfo(
                    "✅ Remise cree",
                    f"Cheques\n{format_montant(total)}\nStock mis à jour."
                )
                self.notebook.select(1)
                self._charger_attente()
                self._charger_stock()

            except (IOError, ValueError, KeyError) as err:
                _log.error(f"Erreur remise cheques: {err}", exc_info=True)
                lbl_err.config(text=f"❌ Erreur: {str(err)}")
                btn_valider_cheq.config(state="normal", text="✅ Valider")

        btn_valider_cheq = tk.Button(
            btn_f, text="✅ Valider",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=16, pady=6,
            command=_valider_cheq
        )
        btn_valider_cheq.pack(side="left", padx=8)  # type: ignore

        tk.Button(btn_f, text="❌ Annuler",
                  bg="#f38ba8", fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=16, pady=6,
                  command=lambda: (canvas_c.unbind_all("<MouseWheel>"), win.destroy())
                  ).pack(side="left", padx=8)  # type: ignore

        win.bind("<Escape>", lambda e: (canvas_c.unbind_all("<MouseWheel>"), win.destroy()))

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 2: EN ATTENTE
    # ═══════════════════════════════════════════════════════════════
    def _build_attente(self, parent: tk.Widget) -> None:
        """Affiche les remises en attente."""
        _log.debug("[MODULE3][UI] _build_attente appele")
        cols = ("id", "date", "caisse", "type", "total")
        self.tree_attente = ttk.Treeview(
            parent, columns=cols, show="headings", height=14)
        headers = {
            "id": ("ID", 50),
            "date": ("Date", 110),
            "caisse": ("Source", 80),
            "type": ("Type", 130),
            "total": ("Montant", 100),
        }
        for col, (text, width) in headers.items():
            self.tree_attente.heading(col, text=text)
            self.tree_attente.column(col, width=width, anchor="center")

        scroll = ttk.Scrollbar(parent, orient="vertical",
                               command=self.tree_attente.yview)
        self.tree_attente.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")  # type: ignore
        self.tree_attente.pack(fill="both", expand=True, padx=10, pady=10)  # type: ignore

        # ── Boutons ──
        btn_frame = tk.Frame(parent, bg="#1e1e2e")
        btn_frame.pack(pady=8)

        tk.Button(
            btn_frame, text="✅ Marquer comme remis",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4,
            command=self._marquer_remis
        ).pack(side="left", padx=4)  # type: ignore

        tk.Button(
            btn_frame, text="🔄 Rafraichir",
            bg="#313244", fg="#cdd6f4",
            font=FONT_MONO, relief="flat", padx=12, pady=4,
            command=self._charger_attente
        ).pack(side="left", padx=4)  # type: ignore

        self._charger_attente()

    def _charger_attente(self) -> None:
        """Charge et affiche les remises en attente."""
        _log.debug("[MODULE3][UI] _charger_attente appele")
        for item in self.tree_attente.get_children():
            self.tree_attente.delete(item)

        remises_list = remises.get_remises_en_attente()
        for remise in remises_list:
            montant = remise.get("montant_total", 0)
            self.tree_attente.insert("", "end", values=(
                remise.get("id", ""),
                remise.get("date_remise", ""),
                remise.get("num_caisse", ""),
                remise.get("type_remise", ""),
                format_montant(montant),
            ))

    def _marquer_remis(self) -> None:
        """Marque la remise selectionnee comme remise."""
        _log.debug("[MODULE3][UI] _marquer_remis appele")
        sel = self.tree_attente.selection()
        if not sel:
            messagebox.showwarning("⚠️ Selection", "Selectionnez une remise.")
            return

        item = sel[0]
        vals = self.tree_attente.item(item, "values")
        remise_id = vals[0]

        if messagebox.askyesno(
                "Confirmer",
                f"Marquer la remise #{remise_id} comme remise en banque ?"):
            _log.info(f"Marque remise {remise_id} comme remise")
            remises.marquer_remis(remise_id)
            self._charger_attente()
            self._charger_stock()
            self._charger_historique()

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 3: HISTORIQUE
    # ═══════════════════════════════════════════════════════════════
    def _build_historique(self, parent: tk.Widget) -> None:
        """Affiche l'historique des remises."""
        _log.debug("[MODULE3][UI] _build_historique appele")
        cols = ("id", "date", "caisse", "type", "total", "statut")
        self.tree_histo = ttk.Treeview(
            parent, columns=cols, show="headings", height=14)
        headers = {
            "id": ("ID", 50),
            "date": ("Date", 110),
            "caisse": ("Source", 80),
            "type": ("Type", 130),
            "total": ("Montant", 100),
            "statut": ("Statut", 100),
        }
        for col, (text, width) in headers.items():
            self.tree_histo.heading(col, text=text)
            self.tree_histo.column(col, width=width, anchor="center")

        scroll = ttk.Scrollbar(parent, orient="vertical",
                               command=self.tree_histo.yview)
        self.tree_histo.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")  # type: ignore
        self.tree_histo.pack(fill="both", expand=True, padx=10, pady=10)  # type: ignore

        # ── Boutons ──
        btn_frame = tk.Frame(parent, bg="#1e1e2e")
        btn_frame.pack(pady=8)

        tk.Button(
            btn_frame, text="🔄 Rafraichir",
            bg="#313244", fg="#cdd6f4",
            font=FONT_MONO, relief="flat", padx=12, pady=4,
            command=self._charger_historique
        ).pack(side="left", padx=4)  # type: ignore

        self._charger_historique()

    def _charger_historique(self) -> None:
        """Charge et affiche l'historique."""
        _log.debug("[MODULE3][UI] _charger_historique appele")
        for item in self.tree_histo.get_children():
            self.tree_histo.delete(item)

        remises_list = remises.get_historique()
        for remise in remises_list:
            montant = remise.get("montant_total", 0)
            self.tree_histo.insert("", "end", values=(
                remise.get("id", ""),
                remise.get("date_remise", ""),
                remise.get("num_caisse", ""),
                remise.get("type_remise", ""),
                format_montant(montant),
                "✅ Remis" if remise.get("statut_banque") else "⏳ En attente",
            ))

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 4: ECHANGES
    # ═══════════════════════════════════════════════════════════════
    def _build_echanges_tab(self, parent: tk.Widget) -> None:
        """Onglet pour echanger pieces <-> billets (cote à cote)."""
        _log.debug("[MODULE3][UI] _build_echanges_tab appele")
        parent.configure(bg="#1e1e2e")

        # ── En-tete ──
        header = tk.Frame(parent, bg="#1e1e2e")
        header.pack(fill="x", padx=14, pady=(10, 4))  # type: ignore
        tk.Label(header, text="🔄 Echange de pieces et billets",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=FONT_BOLD).pack(side="left")  # type: ignore

        # ── Main: 2 colonnes ──
        main = tk.Frame(parent, bg="#1e1e2e")
        main.pack(fill="both", expand=True, padx=14, pady=8)  # type: ignore

        # ══════════════════════════════════════════════════════════════
        # SECTION 1: DONNER (ce qu'on retire du stock)
        # ══════════════════════════════════════════════════════════════
        col_left = tk.Frame(main, bg="#1e1e2e")
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 8))  # type: ignore

        tk.Label(col_left, text="📤 Vous donnez :", bg="#1e1e2e", fg="#f38ba8",
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 2))

        frame_donner = tk.Frame(col_left, bg="#2a2a3e", relief="groove", bd=1)
        frame_donner.pack(fill="x", pady=4, padx=8)

        vars_donner: dict[str, tk.IntVar] = {}

        # Pieces à donner
        tk.Label(frame_donner, text="Pieces :", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(4, 0))

        for piece in ["2", "1", "0.5", "0.2", "0.1", "0.05", "0.02", "0.01"]:
            row = tk.Frame(frame_donner, bg="#2a2a3e")
            row.pack(fill="x", padx=12, pady=2)  # type: ignore
            tk.Label(row, text=f"{piece} €", bg="#2a2a3e", fg="#cdd6f4",
                     font=FONT_MONO, width=6).pack(side="left")  # type: ignore
            var = tk.IntVar(value=0)
            vars_donner[f"piece_{piece}"] = var
            tk.Spinbox(row, from_=0, to=999, textvariable=var,
                       bg="#313244", fg="#cdd6f4",
                       font=FONT_MONO, width=8).pack(side="left", padx=4)  # type: ignore

        # Billets à donner
        tk.Label(frame_donner, text="Billets :", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 0))

        for billet in ["500", "200", "100", "50", "20", "10", "5", "2", "1"]:
            row = tk.Frame(frame_donner, bg="#2a2a3e")
            row.pack(fill="x", padx=12, pady=2)  # type: ignore
            tk.Label(row, text=f"{billet} €", bg="#2a2a3e", fg="#cdd6f4",
                     font=FONT_MONO, width=6).pack(side="left")  # type: ignore
            var = tk.IntVar(value=0)
            vars_donner[f"billet_{billet}"] = var
            tk.Spinbox(row, from_=0, to=999, textvariable=var,
                       bg="#313244", fg="#cdd6f4",
                       font=FONT_MONO, width=8).pack(side="left", padx=4)  # type: ignore

        lbl_donner_total = tk.Label(frame_donner, text="Total donne : 0.00 €",
                                     bg="#2a2a3e", fg="#f38ba8",
                                     font=("Segoe UI", 10, "bold"))
        lbl_donner_total.pack(pady=6)

        # ══════════════════════════════════════════════════════════════
        # SECTION 2: RECEVOIR (ce qu'on ajoute au stock)
        # ══════════════════════════════════════════════════════════════
        col_right = tk.Frame(main, bg="#1e1e2e")
        col_right.pack(side="left", fill="both", expand=True, padx=(8, 0))  # type: ignore

        tk.Label(col_right, text="📥 Vous recevez :", bg="#1e1e2e", fg="#a6e3a1",
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 2))

        frame_recevoir = tk.Frame(col_right, bg="#2a2a3e", relief="groove", bd=1)
        frame_recevoir.pack(fill="x", pady=4, padx=8)

        vars_recevoir: dict[str, tk.IntVar] = {}

        # Pieces à recevoir
        tk.Label(frame_recevoir, text="Pieces :", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(4, 0))

        for piece in ["2", "1", "0.5", "0.2", "0.1", "0.05", "0.02", "0.01"]:
            row = tk.Frame(frame_recevoir, bg="#2a2a3e")
            row.pack(fill="x", padx=12, pady=2)  # type: ignore
            tk.Label(row, text=f"{piece} €", bg="#2a2a3e", fg="#cdd6f4",
                     font=FONT_MONO, width=6).pack(side="left")  # type: ignore
            var = tk.IntVar(value=0)
            vars_recevoir[f"piece_{piece}"] = var
            tk.Spinbox(row, from_=0, to=999, textvariable=var,
                       bg="#313244", fg="#cdd6f4",
                       font=FONT_MONO, width=8).pack(side="left", padx=4)  # type: ignore

        # Billets à recevoir
        tk.Label(frame_recevoir, text="Billets :", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 0))

        for billet in ["500", "200", "100", "50", "20", "10", "5", "2", "1"]:
            row = tk.Frame(frame_recevoir, bg="#2a2a3e")
            row.pack(fill="x", padx=12, pady=2)  # type: ignore
            tk.Label(row, text=f"{billet} €", bg="#2a2a3e", fg="#cdd6f4",
                     font=FONT_MONO, width=6).pack(side="left")  # type: ignore
            var = tk.IntVar(value=0)
            vars_recevoir[f"billet_{billet}"] = var
            tk.Spinbox(row, from_=0, to=999, textvariable=var,
                       bg="#313244", fg="#cdd6f4",
                       font=FONT_MONO, width=8).pack(side="left", padx=4)  # type: ignore

        lbl_recevoir_total = tk.Label(frame_recevoir, text="Total recu : 0.00 €",
                                       bg="#2a2a3e", fg="#a6e3a1",
                                       font=("Segoe UI", 10, "bold"))
        lbl_recevoir_total.pack(pady=6)

        # ══════════════════════════════════════════════════════════════
        # BILAN
        # ══════════════════════════════════════════════════════════════
        frame_bilan = tk.Frame(parent, bg="#1e1e2e", relief="groove", bd=1)
        frame_bilan.pack(fill="x", padx=14, pady=8)  # type: ignore

        lbl_bilan = tk.Label(frame_bilan, text="EQUILIBRE ✅",
                             bg="#1e1e2e", fg="#a6e3a1",
                             font=("Segoe UI", 10, "bold"))
        lbl_bilan.pack(pady=6)

        # ══════════════════════════════════════════════════════════════
        # FONCTION UPDATE TOTAUX
        # ══════════════════════════════════════════════════════════════
        def _update_echange_totals(*_: tk.Event) -> None:  # type: ignore
            total_donner = 0.0
            total_recevoir = 0.0

            # Calculer ce qu'on donne
            for key_d, var_d in vars_donner.items():
                coupure_str = key_d.split("_")[1]
                coupure = float(coupure_str)
                total_donner += coupure * var_d.get()

            # Calculer ce qu'on recoit
            for key_r, var_r in vars_recevoir.items():
                coupure_str = key_r.split("_")[1]
                coupure = float(coupure_str)
                total_recevoir += coupure * var_r.get()

            # Afficher
            lbl_donner_total.config(text=f"Total donne : {format_montant(total_donner)}")
            lbl_recevoir_total.config(text=f"Total recu : {format_montant(total_recevoir)}")

            # Bilan
            diff = total_recevoir - total_donner
            if abs(diff) < 0.01:  # Equilibre
                lbl_bilan.config(text="EQUILIBRE ✅", fg="#a6e3a1")
                btn_valider_echange.config(state="normal")
            elif diff > 0:  # On recoit plus
                lbl_bilan.config(
                    text=f"Surplus : +{format_montant(diff)} 📥", fg="#f9e2af")
                btn_valider_echange.config(state="normal")
            else:  # On donne plus
                lbl_bilan.config(
                    text=f"Deficit : {format_montant(abs(diff))} 📤", fg="#f38ba8")
                btn_valider_echange.config(state="disabled")

        # ══════════════════════════════════════════════════════════════
        # BOUTONS
        # ══════════════════════════════════════════════════════════════
        btn_frame = tk.Frame(parent, bg="#1e1e2e")
        btn_frame.pack(side="bottom", pady=8)

        def _valider_echange() -> None:
            _log.debug("[MODULE3][UI] Validation echange")
            btn_valider_echange.config(state="disabled", text="⏳ Traitement...")
            parent.update()

            try:
                # Creer le detail
                changes: dict[str, dict] = {"especes": {}}

                for key_d, var_d in vars_donner.items():
                    qte = var_d.get()
                    if qte > 0:
                        coupure = key_d.split("_")[1]
                        if coupure not in changes["especes"]:
                            changes["especes"][coupure] = 0
                        changes["especes"][coupure] -= qte
                        _log.debug(f"  📤 -{qte}× {coupure}€")

                for key_r, var_r in vars_recevoir.items():
                    qte = var_r.get()
                    if qte > 0:
                        coupure = key_r.split("_")[1]
                        if coupure not in changes["especes"]:
                            changes["especes"][coupure] = 0
                        changes["especes"][coupure] += qte
                        _log.debug(f"  📥 +{qte}× {coupure}€")

                if not any(changes["especes"].values()):
                    messagebox.showwarning("⚠️ Vide", "Saisis un echange!")
                    btn_valider_echange.config(state="normal", text="✅ Valider")
                    return

                try:
                    # Appliquer les changements au stock
                    stock.modifier_stock_direct(changes)
                    _log.info("Stock modifie apres echange")

                    messagebox.showinfo("✅ Echange effectue",
                                       "Les pieces et billets ont ete echanges.")

                    # Reinitialiser les champs
                    for var_donner in vars_donner.values():
                        var_donner.set(0)
                    for var_recvr in vars_recevoir.values():
                        var_recvr.set(0)
                    _update_echange_totals()

                except (IOError, ValueError, KeyError) as err:
                    _log.error(f"Erreur echange: {err}", exc_info=True)
                    messagebox.showerror("❌ Erreur", str(err))
                    btn_valider_echange.config(state="normal", text="✅ Valider")

            except Exception as err:
                _log.error(f"Erreur echange globale: {err}", exc_info=True)
                messagebox.showerror("❌ Erreur", str(err))
                btn_valider_echange.config(state="normal", text="✅ Valider")

        btn_valider_echange = tk.Button(
            btn_frame, text="✅ Valider l'echange",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=16, pady=6,
            command=_valider_echange
        )
        btn_valider_echange.pack(side="left", padx=4)  # type: ignore

        tk.Button(
            btn_frame, text="🔄 Reinitialiser",
            bg="#313244", fg="#cdd6f4",
            font=("Segoe UI", 10),
            relief="flat", padx=16, pady=6,
            command=lambda: (
                [v.set(0) for v in vars_donner.values()],
                [v.set(0) for v in vars_recevoir.values()],
                _update_echange_totals()
            )
        ).pack(side="left", padx=4)  # type: ignore

        _update_echange_totals()


__all__ = ["RemiseUI"]
