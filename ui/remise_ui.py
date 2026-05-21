# ═══════════════════════════════════════════════════════════════════════════════
# FILE: ui/remise_ui.py — COMPLET ET CORRIGÉ
# ═══════════════════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path
from datetime import datetime
import traceback

from core.remise_banque import (
    get_remises_en_attente,
    get_historique,
    marquer_remis,
    ajouter_remise
)
from core.stock import (
    get_stock,
    get_total_cheques,
    reset_stock,
    retirer_remise
)

TYPE_LABELS = {
    "especes": ("💶 Espèces", "#a6e3a1"),
    "cheques_vac": ("🏖️ Chèques Vacances", "#f9e2af"),
    "cheques": ("📄 Chèques", "#cba6f7"),
}

COUPURES_ESPECES = ["500", "200", "100", "50", "20", "10", "5", "2", "1",
                    "0.5", "0.2", "0.1", "0.05", "0.02", "0.01"]
COUPURES_CHEQ_VAC = ["50", "25", "20", "10"]


# ─── HELPERS ───────────────────────────────────────────────────────
def _parse_detail(detail):
    """Convertit le detail en dict."""
    if isinstance(detail, dict):
        return detail
    if isinstance(detail, str):
        try:
            return json.loads(detail)
        except Exception:
            return {}
    return {}


def _qte(info) -> int:
    """Extrait la quantité de plusieurs formats."""
    try:
        if isinstance(info, dict):
            return int(info.get("quantite", 0))
        return int(info)
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════
class RemiseUI(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1e1e2e")
        self._build()

    def _build(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

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
        self.notebook.add(tab4, text="🔄 Échanges")
        self._build_echanges(tab4)

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 1: STOCK
    # ═══════════════════════════════════════════════════════════════
    def _build_stock(self, parent):
        """Affiche le stock actuel avec boutons de remise."""
        parent.configure(bg="#1e1e2e")

        # ── En-tête ──
        header = tk.Frame(parent, bg="#1e1e2e")
        header.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(header, text="📦 Stock actuel",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 12, "bold")).pack(side="left")

        tk.Button(header, text="🔄 Rafraîchir",
                  bg="#313244", fg="#cdd6f4",
                  font=("Segoe UI", 9), relief="flat", padx=10, pady=4,
                  command=self._charger_stock).pack(side="right", padx=4)

        tk.Button(header, text="🗑️ Reset (test)",
                  bg="#f38ba8", fg="#1e1e2e",
                  font=("Segoe UI", 9), relief="flat", padx=10, pady=4,
                  command=self._reset_stock).pack(side="right", padx=4)

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
        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=10)

        self._charger_stock()

    def _charger_stock(self):
        """Charge et affiche le stock."""
        for w in self._frame_stock.winfo_children():
            w.destroy()

        stock = get_stock()
        maj = stock.get("derniere_maj") or "jamais"
        self._lbl_maj.config(text=f"Dernière mise à jour : {maj}")

        # ── ESPÈCES ──
        especes_raw = stock.get("especes", {})
        especes_norm = {c: _qte(especes_raw.get(c, 0))
                        for c in COUPURES_ESPECES}
        billets_esp = {c: q for c, q in especes_norm.items() if q > 0}
        total_esp = sum(float(c) * q for c, q in billets_esp.items())

        self._afficher_carte_stock(
            type_remise="especes",
            billets=especes_norm if billets_esp else None,
            total=total_esp
        )

        # ── CHÈQUES VACANCES ──
        cheq_vac_raw = stock.get("cheques_vac", {})
        cheq_vac_norm = {c: _qte(cheq_vac_raw.get(c, 0))
                         for c in COUPURES_CHEQ_VAC}
        billets_vac = {c: q for c, q in cheq_vac_norm.items() if q > 0}
        total_vac = sum(float(c) * q for c, q in billets_vac.items())

        self._afficher_carte_stock(
            type_remise="cheques_vac",
            billets=cheq_vac_norm,
            total=total_vac
        )

        # ── CHÈQUES ──
        cheques = stock.get("cheques", [])
        total_cheq = sum(ch.get("montant", 0.0) for ch in cheques)

        self._afficher_carte_stock(
            type_remise="cheques",
            cheques=cheques,
            total=total_cheq
        )

    def _afficher_carte_stock(self, type_remise: str, billets=None,
                              cheques=None, total=0.0):
        """Affiche une carte pour un type de remise."""
        label, color = TYPE_LABELS.get(type_remise, (type_remise, "#cdd6f4"))

        card = tk.Frame(self._frame_stock, bg="#2a2a3e",
                        relief="flat", highlightthickness=0)
        card.pack(fill="x", pady=8)

        # ── En-tête ──
        row = tk.Frame(card, bg="#2a2a3e")
        row.pack(fill="x")

        tk.Label(row, text=f"Total : {total:.2f} €",
                 bg="#2a2a3e", fg=color,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=12, pady=8)

        tk.Button(
            row,
            text="🏦 Remettre en banque",
            bg="#313244", fg=color,
            font=("Segoe UI", 9), relief="flat", padx=8, pady=2,
            command=lambda t=type_remise: self._dialog_remise(t)
        ).pack(side="right", padx=12, pady=8)

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
                for coupure in liste:
                    qte = billets.get(coupure, 0)
                    if type_remise == "especes" and qte == 0:
                        continue
                    any_shown = True
                    montant = float(coupure) * qte
                    couleur = "#cdd6f4" if qte > 0 else "#45475a"
                    tk.Label(card,
                             text=f"  {coupure} € × {qte} = {montant:.2f} €",
                             bg="#2a2a3e", fg=couleur,
                             font=("Segoe UI", 8)).pack(anchor="w", padx=12)

                if not any_shown:
                    tk.Label(card, text="— aucun billet en stock —",
                             bg="#2a2a3e", fg="#6c7086",
                             font=("Segoe UI", 8, "italic")).pack(
                        anchor="w", padx=12, pady=4)

        # ── Détail chèques ──
        elif cheques is not None and cheques:
            tk.Label(card, text="Détail :",
                     bg="#2a2a3e", fg="#6c7086",
                     font=("Segoe UI", 8, "italic")).pack(
                anchor="w", padx=12, pady=(4, 0))

            for ch in cheques:
                num = ch.get("num", "—")
                mont = ch.get("montant", 0.0)
                caisse = ch.get("caisse", "")
                txt = f"  N° {num} → {mont:.2f} €"
                if caisse:
                    txt += f" (caisse {caisse})"
                tk.Label(card, text=txt,
                         bg="#2a2a3e", fg="#cdd6f4",
                         font=("Segoe UI", 8)).pack(anchor="w", padx=12)

    def _reset_stock(self):
        """Réinitialise le stock."""
        if messagebox.askyesno(
                "⚠️ Reset stock",
                "Remettre le stock à zéro ?\n"
                "À utiliser uniquement pour les tests.",
                icon="warning"
        ):
            reset_stock()
            self._charger_stock()

    # ═══════════════════════════════════════════════════════════════
    # DIALOGUES REMISE
    # ═══════════════════════════════════════════════════════════════
    def _dialog_remise(self, type_remise: str):
        """Dispatcher vers le bon dialogue."""
        print(f"\n🔍 [DEBUG DIALOG] Ouverture dialog remise: {type_remise}")
        stock = get_stock()
        print(f"🔍 [DEBUG DIALOG] Stock complet: {stock}")

        if type_remise == "cheques":
            self._dialog_cheques(stock.get("cheques", []))
        else:
            self._dialog_coupures(type_remise, stock)

    def _dialog_coupures(self, type_remise: str, stock: dict):
        """Dialogue pour Espèces et Chèques Vacances."""
        print(f"\n🔍 [DEBUG _dialog_coupures] type_remise={type_remise}")

        label, color = TYPE_LABELS[type_remise]
        liste_coupures = (COUPURES_ESPECES if type_remise == "especes"
                          else COUPURES_CHEQ_VAC)

        raw = stock.get(type_remise, {})
        print(f"🔍 [DEBUG _dialog_coupures] raw data: {raw}")

        billets_norm = {c: _qte(raw.get(c, 0)) for c in liste_coupures}
        print(f"🔍 [DEBUG _dialog_coupures] billets_norm: {billets_norm}")

        if type_remise == "especes":
            coupures_affichees = [(c, billets_norm[c])
                                  for c in liste_coupures
                                  if billets_norm[c] > 0]
        else:
            coupures_affichees = [(c, billets_norm[c])
                                  for c in liste_coupures]

        print(f"🔍 [DEBUG _dialog_coupures] coupures_affichees: {coupures_affichees}")

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
                 font=("Segoe UI", 13, "bold")).pack(pady=(14, 4))

        # ── Date ──
        frame_dt = tk.Frame(win, bg="#1e1e2e")
        frame_dt.pack(pady=4)
        tk.Label(frame_dt, text="Date :",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        var_date = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        tk.Entry(frame_dt, textvariable=var_date,
                 bg="#313244", fg="#cdd6f4",
                 font=("Segoe UI", 10), width=12, justify="center",
                 insertbackground="#cdd6f4", relief="flat").pack(side="left")

        tk.Label(win, text="Sélectionnez les coupures à remettre :",
                 bg="#1e1e2e", fg="#6c7086",
                 font=("Segoe UI", 9, "italic")).pack(pady=(6, 2))

        # ── Tableau ──
        frame_canvas = tk.Frame(win, bg="#2a2a3e", relief="groove", bd=1)
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=4)

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
        vsb.pack(side="right", fill="y")
        canvas_t.pack(fill="both", expand=True)

        def _mwheel(event):
            canvas_t.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas_t.bind_all("<MouseWheel>", _mwheel)

        vars_qte = {}
        lbl_sts = {}
        lbl_total_var = tk.StringVar(value="0.00 €")

        def _update_total(*_):
            total = 0.0
            for coupure, var in vars_qte.items():
                qte = var.get()
                montant = float(coupure) * qte
                lbl_sts[coupure].config(text=f"{montant:.2f} €")
                total += montant
            lbl_total_var.set(f"{total:.2f} €")
            print(f"🔍 [UPDATE TOTAL] {total:.2f} €")

        for row_i, (coupure, qte_stock_val) in enumerate(coupures_affichees):
            tk.Label(frame_table, text=f"{coupure} €",
                     bg="#2a2a3e", fg="#cdd6f4",
                     font=("Segoe UI", 9, "bold")).grid(
                row=row_i, column=0, sticky="w", padx=6, pady=3)

            tk.Label(frame_table, text=f"× {qte_stock_val}",
                     bg="#2a2a3e", fg="#6c7086",
                     font=("Segoe UI", 9), width=8).grid(
                row=row_i, column=1, padx=6, pady=3)

            var = tk.IntVar(value=0)
            vars_qte[coupure] = var

            tk.Spinbox(
                frame_table, from_=0, to=qte_stock_val, textvariable=var,
                bg="#313244", fg="#cdd6f4",
                font=("Segoe UI", 9), width=6,
                command=_update_total
            ).grid(row=row_i, column=2, padx=6, pady=3)

            lbl_st = tk.Label(frame_table, text="0.00 €",
                              bg="#2a2a3e", fg="#6c7086",
                              font=("Segoe UI", 9), width=12, anchor="e")
            lbl_st.grid(row=row_i, column=3, padx=6, pady=3)
            lbl_sts[coupure] = lbl_st

        # ── Total ──
        frame_tot = tk.Frame(win, bg="#1e1e2e")
        frame_tot.pack(pady=8)
        tk.Label(frame_tot, text="Total :",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 8))
        tk.Label(frame_tot, textvariable=lbl_total_var,
                 bg="#1e1e2e", fg=color,
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        lbl_err = tk.Label(win, text="", bg="#1e1e2e", fg="#f38ba8",
                           font=("Segoe UI", 8))
        lbl_err.pack()

        def valider():
            print(f"\n🔍 [DEBUG VALIDER {type_remise.upper()}]")
            btn_valider.config(state="disabled", text="⏳ Traitement...")
            win.update()

            try:
                try:
                    date_obj = datetime.strptime(
                        var_date.get().strip(), "%d/%m/%Y")
                    date_str = date_obj.strftime("%Y-%m-%d")
                    print(f"✅ Date OK: {date_str}")
                except ValueError as e:
                    print(f"❌ Erreur date: {e}")
                    lbl_err.config(
                        text="⚠️ Date invalide (JJ/MM/AAAA)")
                    btn_valider.config(state="normal", text="✅ Valider")
                    return

                # ✅ CRÉER LE DETAIL CORRECT
                detail = {
                    "billets": {},
                    "total": 0.0
                }

                for coupure, var in vars_qte.items():
                    qte = var.get()
                    if qte > 0:
                        montant = float(coupure) * qte
                        detail["billets"][coupure] = {
                            "quantite": qte,
                            "montant": montant
                        }
                        detail["total"] += montant

                total = detail["total"]

                print(f"🔍 [DEBUG VALIDER] Detail: {detail}")
                print(f"🔍 [DEBUG VALIDER] Total: {total}")

                if total <= 0:
                    print(f"❌ Total <= 0")
                    lbl_err.config(text="⚠️ Sélectionnez au moins un billet")
                    btn_valider.config(state="normal", text="✅ Valider")
                    return

                if not messagebox.askyesno(
                        "Confirmer la remise",
                        f"{label}\nTotal : {total:.2f} €\n\nCréer la remise ?",
                        parent=win
                ):
                    print(f"❌ Utilisateur a annulé")
                    btn_valider.config(state="normal", text="✅ Valider")
                    return

                print(f"✅ Utilisateur a confirmé")

                # ✅ CRÉER LA REMISE AVEC LE BON DETAIL
                print(f"🔍 [DEBUG VALIDER] Création remise...")
                ajouter_remise(
                    date_caisse=date_str,
                    num_caisse="MANUEL",
                    type_remise=type_remise,
                    detail=detail,
                )
                print(f"✅ Remise créée en BDD")

                # ✅ DÉCRÉMENTER LE STOCK
                print(f"🔍 [DEBUG VALIDER] Déduction stock...")
                retirer_remise(type_remise, detail)
                print(f"✅ Stock déduit")

                canvas_t.unbind_all("<MouseWheel>")
                win.destroy()

                messagebox.showinfo(
                    "✅ Remise créée",
                    f"{label}\n{total:.2f} €\nStock mis à jour."
                )
                self.notebook.select(1)
                self._charger_attente()
                self._charger_stock()

            except Exception as e:
                print(f"\n❌ ERREUR EXCEPTION:")
                print(traceback.format_exc())
                lbl_err.config(text=f"❌ Erreur: {str(e)}")
                btn_valider.config(state="normal", text="✅ Valider")

        btn_f = tk.Frame(win, bg="#1e1e2e")
        btn_f.pack(side="bottom", pady=8)

        btn_valider = tk.Button(
            btn_f, text="✅ Valider",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=16, pady=6,
            command=valider
        )
        btn_valider.pack(side="left", padx=8)

        tk.Button(btn_f, text="❌ Annuler",
                  bg="#f38ba8", fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=16, pady=6,
                  command=lambda: [
                      canvas_t.unbind_all("<MouseWheel>"),
                      win.destroy()
                  ]).pack(side="left", padx=8)

        win.bind("<Escape>", lambda e: [
            canvas_t.unbind_all("<MouseWheel>"), win.destroy()])

    def _dialog_cheques(self, cheques):
        """Dialogue pour les chèques."""
        print(f"\n🔍 [DEBUG _dialog_cheques] Chèques: {cheques}")

        label, color = TYPE_LABELS["cheques"]

        hauteur = max(400, min(100 + len(cheques) * 34 + 150, 700))
        win = tk.Toplevel(self)
        win.title(f"Remise — {label}")
        win.configure(bg="#1e1e2e")
        win.resizable(False, True)
        win.grab_set()
        win.geometry(f"500x{hauteur}")
        x = self.winfo_toplevel().winfo_x() + 150
        y = self.winfo_toplevel().winfo_y() + 60
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text=f"🏦 Remise — {label}",
                 bg="#1e1e2e", fg=color,
                 font=("Segoe UI", 13, "bold")).pack(pady=(14, 4))

        # ── Date ──
        frame_dt = tk.Frame(win, bg="#1e1e2e")
        frame_dt.pack(pady=4)
        tk.Label(frame_dt, text="Date :",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        var_date = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        tk.Entry(frame_dt, textvariable=var_date,
                 bg="#313244", fg="#cdd6f4",
                 font=("Segoe UI", 10), width=12, justify="center",
                 insertbackground="#cdd6f4", relief="flat").pack(side="left")

        tk.Label(win, text="Sélectionnez les chèques à remettre :",
                 bg="#1e1e2e", fg="#6c7086",
                 font=("Segoe UI", 9, "italic")).pack(pady=(6, 2))

        # ── Liste chèques ──
        frame_list = tk.Frame(win, bg="#2a2a3e", relief="groove", bd=1)
        frame_list.pack(fill="both", expand=True, padx=20, pady=4)

        canvas_c = tk.Canvas(frame_list, bg="#2a2a3e",
                             highlightthickness=0)
        vsb = ttk.Scrollbar(frame_list, orient="vertical",
                            command=canvas_c.yview)
        inner = tk.Frame(canvas_c, bg="#2a2a3e")
        inner.bind(
            "<Configure>",
            lambda e: canvas_c.configure(scrollregion=canvas_c.bbox("all"))
        )
        canvas_c.create_window((0, 0), window=inner, anchor="nw")
        canvas_c.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas_c.pack(fill="both", expand=True)

        def _mwheel(event):
            canvas_c.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas_c.bind_all("<MouseWheel>", _mwheel)

        vars_sel = []
        lbl_total_var = tk.StringVar(value="0.00 €")

        def _update_total(*_):
            total = sum(ch.get("montant", 0.0)
                        for v, ch in vars_sel if v.get())
            lbl_total_var.set(f"{total:.2f} €")

        for ch in cheques:
            var = tk.BooleanVar(value=True)
            num = ch.get("num", "—")
            mont = ch.get("montant", 0.0)
            caisse = ch.get("caisse", "")
            txt = f"  N° {num}   →   {mont:.2f} €"
            if caisse:
                txt += f"   (caisse {caisse})"

            row_f = tk.Frame(inner, bg="#2a2a3e")
            row_f.pack(fill="x", padx=8, pady=3)
            tk.Checkbutton(
                row_f, text=txt, variable=var,
                bg="#2a2a3e", fg="#cdd6f4",
                selectcolor="#313244",
                activebackground="#2a2a3e",
                font=("Segoe UI", 9),
                command=_update_total
            ).pack(side="left")
            vars_sel.append((var, ch))

        _update_total()

        # ── Total ──
        frame_tot = tk.Frame(win, bg="#1e1e2e")
        frame_tot.pack(pady=8)
        tk.Label(frame_tot, text="Total :",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 8))
        tk.Label(frame_tot, textvariable=lbl_total_var,
                 bg="#1e1e2e", fg=color,
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        lbl_err = tk.Label(win, text="", bg="#1e1e2e", fg="#f38ba8",
                           font=("Segoe UI", 8))
        lbl_err.pack()

        def valider():
            print(f"\n🔍 [DEBUG VALIDER CHÈQUES]")
            btn_valider.config(state="disabled", text="⏳ Traitement...")
            win.update()

            try:
                try:
                    date_obj = datetime.strptime(
                        var_date.get().strip(), "%d/%m/%Y")
                    date_str = date_obj.strftime("%Y-%m-%d")
                    print(f"✅ Date OK: {date_str}")
                except ValueError as e:
                    print(f"❌ Erreur date: {e}")
                    lbl_err.config(
                        text="⚠️ Date invalide (JJ/MM/AAAA)")
                    btn_valider.config(state="normal", text="✅ Valider")
                    return

                selectionnes = [ch for v, ch in vars_sel if v.get()]

                if not selectionnes:
                    print(f"❌ Aucun chèque sélectionné")
                    lbl_err.config(
                        text="⚠️ Aucun chèque sélectionné")
                    btn_valider.config(state="normal", text="✅ Valider")
                    return

                total = sum(ch.get("montant", 0.0)
                            for ch in selectionnes)
                print(f"🔍 [DEBUG VALIDER CHÈQUES] Total: {total}")

                if not messagebox.askyesno(
                        "Confirmer la remise",
                        f"Chèques — {total:.2f} €\n"
                        f"{len(selectionnes)} chèque(s)\n\n"
                        f"Créer la remise ?",
                        parent=win
                ):
                    print(f"❌ Utilisateur a annulé")
                    btn_valider.config(state="normal", text="✅ Valider")
                    return

                print(f"✅ Utilisateur a confirmé")

                detail = {
                    "total": round(total, 2),
                    "cheques": selectionnes
                }

                print(f"🔍 [DEBUG VALIDER CHÈQUES] Création remise...")
                ajouter_remise(
                    date_caisse=date_str,
                    num_caisse="MANUEL",
                    type_remise="cheques",
                    detail=detail,
                )
                print(f"✅ Remise créée en BDD")

                print(f"🔍 [DEBUG VALIDER CHÈQUES] Déduction stock: {detail}")
                retirer_remise("cheques", detail)
                print(f"✅ Stock déduit")

                canvas_c.unbind_all("<MouseWheel>")
                win.destroy()

                messagebox.showinfo(
                    "✅ Remise créée",
                    f"Chèques\n{total:.2f} €\nStock mis à jour."
                )
                self.notebook.select(1)
                self._charger_attente()
                self._charger_stock()

            except Exception as e:
                print(f"\n❌ ERREUR EXCEPTION:")
                print(traceback.format_exc())
                lbl_err.config(text=f"❌ Erreur: {str(e)}")
                btn_valider.config(state="normal", text="✅ Valider")

        btn_f = tk.Frame(win, bg="#1e1e2e")
        btn_f.pack(side="bottom", pady=8)

        btn_valider = tk.Button(
            btn_f, text="✅ Valider",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=16, pady=6,
            command=valider
        )
        btn_valider.pack(side="left", padx=8)

        tk.Button(btn_f, text="❌ Annuler",
                  bg="#f38ba8", fg="#1e1e2e",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=16, pady=6,
                  command=lambda: [
                      canvas_c.unbind_all("<MouseWheel>"),
                      win.destroy()
                  ]).pack(side="left", padx=8)

        win.bind("<Escape>", lambda e: [
            canvas_c.unbind_all("<MouseWheel>"), win.destroy()])

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 2: EN ATTENTE
    # ═══════════════════════════════════════════════════════════════
    def _build_attente(self, parent):
        """Affiche les remises en attente."""
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
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_attente.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ── Boutons ──
        btn_frame = tk.Frame(parent, bg="#1e1e2e")
        btn_frame.pack(pady=8)

        tk.Button(
            btn_frame, text="✅ Marquer comme remis",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4,
            command=self._marquer_remis
        ).pack(side="left", padx=4)

        tk.Button(
            btn_frame, text="🔄 Rafraîchir",
            bg="#313244", fg="#cdd6f4",
            font=("Segoe UI", 9), relief="flat", padx=12, pady=4,
            command=self._charger_attente
        ).pack(side="left", padx=4)

        self._charger_attente()

    def _charger_attente(self):
        """Charge et affiche les remises en attente."""
        for item in self.tree_attente.get_children():
            self.tree_attente.delete(item)

        remises = get_remises_en_attente()
        for remise in remises:
            self.tree_attente.insert("", tk.END, values=(
                remise.get("id", ""),
                remise.get("date_remise", ""),
                remise.get("num_caisse", ""),
                remise.get("type_remise", ""),
                f"{remise.get('montant_total', 0):.2f}",
            ))

    def _marquer_remis(self):
        """Marque la remise sélectionnée comme remise."""
        sel = self.tree_attente.selection()
        if not sel:
            messagebox.showwarning("⚠️ Sélection", "Sélectionne une remise.")
            return

        item = sel[0]
        vals = self.tree_attente.item(item, "values")
        remise_id = vals[0]

        if messagebox.askyesno(
                "Confirmer",
                f"Marquer la remise #{remise_id} comme remise en banque ?"):
            marquer_remis(remise_id)
            self._charger_attente()
            self._charger_stock()
            self._charger_historique()

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 3: HISTORIQUE
    # ═══════════════════════════════════════════════════════════════
    def _build_historique(self, parent):
        """Affiche l'historique des remises."""
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
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_histo.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ── Boutons ──
        btn_frame = tk.Frame(parent, bg="#1e1e2e")
        btn_frame.pack(pady=8)

        tk.Button(
            btn_frame, text="🔄 Rafraîchir",
            bg="#313244", fg="#cdd6f4",
            font=("Segoe UI", 9), relief="flat", padx=12, pady=4,
            command=self._charger_historique
        ).pack(side="left", padx=4)

        self._charger_historique()

    def _charger_historique(self):
        """Charge et affiche l'historique."""
        for item in self.tree_histo.get_children():
            self.tree_histo.delete(item)

        remises = get_historique()
        for remise in remises:
            self.tree_histo.insert("", tk.END, values=(
                remise.get("id", ""),
                remise.get("date_remise", ""),
                remise.get("num_caisse", ""),
                remise.get("type_remise", ""),
                f"{remise.get('montant_total', 0):.2f}",
                "✅ Remis" if remise.get("statut_banque") else "⏳ En attente",
            ))

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 4: ÉCHANGES
    # ═══════════════════════════════════════════════════════════════
    def _build_echanges(self, parent):
        """Onglet pour échanger pièces ↔ billets (côte à côte)."""
        parent.configure(bg="#1e1e2e")

        # ── En-tête ──
        header = tk.Frame(parent, bg="#1e1e2e")
        header.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(header, text="🔄 Échange de pièces et billets",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 12, "bold")).pack(side="left")

        # ── Main: 2 colonnes ──
        main = tk.Frame(parent, bg="#1e1e2e")
        main.pack(fill="both", expand=True, padx=14, pady=8)

        # ══════════════════════════════════════════════════════════════
        # SECTION 1: DONNER (ce qu'on retire du stock)
        # ══════════════════════════════════════════════════════════════
        col_left = tk.Frame(main, bg="#1e1e2e")
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(col_left, text="📤 Vous donnez :", bg="#1e1e2e", fg="#f38ba8",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 2))

        frame_donner = tk.Frame(col_left, bg="#2a2a3e", relief="groove", bd=1)
        frame_donner.pack(fill="x", pady=4, padx=8)

        vars_donner = {}

        # Pièces à donner
        tk.Label(frame_donner, text="Pièces :", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(4, 0))

        for piece in ["2", "1", "0.5", "0.2", "0.1", "0.05", "0.02", "0.01"]:
            row = tk.Frame(frame_donner, bg="#2a2a3e")
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"{piece} €", bg="#2a2a3e", fg="#cdd6f4",
                     font=("Segoe UI", 9), width=6).pack(side="left")
            var = tk.IntVar(value=0)
            vars_donner[f"piece_{piece}"] = var
            tk.Spinbox(row, from_=0, to=999, textvariable=var,
                       bg="#313244", fg="#cdd6f4",
                       font=("Segoe UI", 9), width=8).pack(side="left", padx=4)

        # Billets à donner
        tk.Label(frame_donner, text="Billets :", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 0))

        for billet in ["500", "200", "100", "50", "20", "10", "5", "2", "1"]:
            row = tk.Frame(frame_donner, bg="#2a2a3e")
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"{billet} €", bg="#2a2a3e", fg="#cdd6f4",
                     font=("Segoe UI", 9), width=6).pack(side="left")
            var = tk.IntVar(value=0)
            vars_donner[f"billet_{billet}"] = var
            tk.Spinbox(row, from_=0, to=999, textvariable=var,
                       bg="#313244", fg="#cdd6f4",
                       font=("Segoe UI", 9), width=8).pack(side="left", padx=4)

        lbl_donner_total = tk.Label(frame_donner, text="Total donné : 0.00 €",
                                     bg="#2a2a3e", fg="#f38ba8",
                                     font=("Segoe UI", 10, "bold"))
        lbl_donner_total.pack(pady=6)

        # ══════════════════════════════════════════════════════════════
        # SECTION 2: RECEVOIR (ce qu'on ajoute au stock)
        # ══════════════════════════════════════════════════════════════
        col_right = tk.Frame(main, bg="#1e1e2e")
        col_right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(col_right, text="📥 Vous recevez :", bg="#1e1e2e", fg="#a6e3a1",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 2))

        frame_recevoir = tk.Frame(col_right, bg="#2a2a3e", relief="groove", bd=1)
        frame_recevoir.pack(fill="x", pady=4, padx=8)

        vars_recevoir = {}

        # Pièces à recevoir
        tk.Label(frame_recevoir, text="Pièces :", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(4, 0))

        for piece in ["2", "1", "0.5", "0.2", "0.1", "0.05", "0.02", "0.01"]:
            row = tk.Frame(frame_recevoir, bg="#2a2a3e")
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"{piece} €", bg="#2a2a3e", fg="#cdd6f4",
                     font=("Segoe UI", 9), width=6).pack(side="left")
            var = tk.IntVar(value=0)
            vars_recevoir[f"piece_{piece}"] = var
            tk.Spinbox(row, from_=0, to=999, textvariable=var,
                       bg="#313244", fg="#cdd6f4",
                       font=("Segoe UI", 9), width=8).pack(side="left", padx=4)

        # Billets à recevoir
        tk.Label(frame_recevoir, text="Billets :", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 0))

        for billet in ["500", "200", "100", "50", "20", "10", "5", "2", "1"]:
            row = tk.Frame(frame_recevoir, bg="#2a2a3e")
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"{billet} €", bg="#2a2a3e", fg="#cdd6f4",
                     font=("Segoe UI", 9), width=6).pack(side="left")
            var = tk.IntVar(value=0)
            vars_recevoir[f"billet_{billet}"] = var
            tk.Spinbox(row, from_=0, to=999, textvariable=var,
                       bg="#313244", fg="#cdd6f4",
                       font=("Segoe UI", 9), width=8).pack(side="left", padx=4)

        lbl_recevoir_total = tk.Label(frame_recevoir, text="Total reçu : 0.00 €",
                                       bg="#2a2a3e", fg="#a6e3a1",
                                       font=("Segoe UI", 10, "bold"))
        lbl_recevoir_total.pack(pady=6)

        # ══════════════════════════════════════════════════════════════
        # BILAN
        # ══════════════════════════════════════════════════════════════
        frame_bilan = tk.Frame(parent, bg="#1e1e2e", relief="groove", bd=1)
        frame_bilan.pack(fill="x", padx=14, pady=8)

        lbl_bilan = tk.Label(frame_bilan, text="ÉQUILIBRÉ ✅",
                             bg="#1e1e2e", fg="#a6e3a1",
                             font=("Segoe UI", 10, "bold"))
        lbl_bilan.pack(pady=6)

        # ══════════════════════════════════════════════════════════════
        # FONCTION UPDATE TOTAUX
        # ══════════════════════════════════════════════════════════════
        def _update_echange(*_):
            total_donner = 0.0
            total_recevoir = 0.0

            # Calculer ce qu'on donne
            for key, var in vars_donner.items():
                coupure_str = key.split("_")[1]
                coupure = float(coupure_str)
                total_donner += coupure * var.get()

            # Calculer ce qu'on reçoit
            for key, var in vars_recevoir.items():
                coupure_str = key.split("_")[1]
                coupure = float(coupure_str)
                total_recevoir += coupure * var.get()

            # Afficher
            lbl_donner_total.config(text=f"Total donné : {total_donner:.2f} €")
            lbl_recevoir_total.config(text=f"Total reçu : {total_recevoir:.2f} €")

            # Bilan
            diff = total_recevoir - total_donner
            if abs(diff) < 0.01:  # Équilibré
                lbl_bilan.config(text="ÉQUILIBRÉ ✅", fg="#a6e3a1")
                btn_valider.config(state="normal")
            elif diff > 0:  # On reçoit plus
                lbl_bilan.config(text=f"Surplus : +{diff:.2f} € 📥", fg="#f9e2af")
                btn_valider.config(state="normal")
            else:  # On donne plus
                lbl_bilan.config(text=f"Manque : {diff:.2f} € 📤", fg="#f38ba8")
                btn_valider.config(state="disabled")

        # Bind tous les spinbox
        for var in list(vars_donner.values()) + list(vars_recevoir.values()):
            var.trace("w", _update_echange)

        # ══════════════════════════════════════════════════════════════
        # BOUTONS
        # ══════════════════════════════════════════════════════════════
        btn_frame = tk.Frame(parent, bg="#1e1e2e")
        btn_frame.pack(pady=12)

        def valider_echange():
            print(f"\n🔍 [DEBUG ÉCHANGE]")

            # Récupérer le stock actuel
            stock = get_stock()

            # Préparer les changements
            changes = {"especes": {}}

            # Retirer ce qu'on donne
            for key, var in vars_donner.items():
                qte = var.get()
                if qte > 0:
                    coupure = key.split("_")[1]
                    if coupure not in changes["especes"]:
                        changes["especes"][coupure] = 0
                    changes["especes"][coupure] -= qte
                    print(f"  📤 -{qte}× {coupure}€")

            # Ajouter ce qu'on reçoit
            for key, var in vars_recevoir.items():
                qte = var.get()
                if qte > 0:
                    coupure = key.split("_")[1]
                    if coupure not in changes["especes"]:
                        changes["especes"][coupure] = 0
                    changes["especes"][coupure] += qte
                    print(f"  📥 +{qte}× {coupure}€")

            if not any(changes["especes"].values()):
                messagebox.showwarning("⚠️ Vide", "Saisis un échange!")
                return

            try:
                # Appliquer les changements au stock
                from core.stock import modifier_stock_direct
                modifier_stock_direct(changes)
                print(f"✅ Stock modifié")

                messagebox.showinfo("✅ Échange effectué",
                                   "Les pièces et billets ont été échangés.")

                # Réinitialiser les champs
                for var in list(vars_donner.values()) + list(vars_recevoir.values()):
                    var.set(0)
                _update_echange()

            except Exception as e:
                print(f"❌ Erreur: {e}")
                messagebox.showerror("❌ Erreur", str(e))

        btn_valider = tk.Button(
            btn_frame, text="✅ Valider l'échange",
            bg="#a6e3a1", fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=16, pady=6,
            command=valider_echange
        )
        btn_valider.pack(side="left", padx=4)

        tk.Button(
            btn_frame, text="🔄 Réinitialiser",
            bg="#313244", fg="#cdd6f4",
            font=("Segoe UI", 10),
            relief="flat", padx=16, pady=6,
            command=lambda: [var.set(0) for var in list(vars_donner.values()) + list(vars_recevoir.values())] + [_update_echange()]
        ).pack(side="left", padx=4)

        _update_echange()
