import sys
import datetime
import logging
import threading
import subprocess
from typing import Callable, Literal, cast
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from config import DOSSIER_BRUT, DOSSIER_SORTIE
from core.dispatcher import traiter_fichier
from ui.progression import ProgressionWindow

logger = logging.getLogger("ui.transform_view")

# ── Constantes Tkinter typées ─────────────────────────────────────────────────
_X        = cast(Literal["none", "x", "y", "both"],                    "x")
_Y        = cast(Literal["none", "x", "y", "both"],                    "y")
_BOTH     = cast(Literal["none", "x", "y", "both"],                    "both")
_LEFT     = cast(Literal["left", "right", "top", "bottom"],            "left")
_RIGHT    = cast(Literal["left", "right", "top", "bottom"],            "right")
_TOP      = cast(Literal["left", "right", "top", "bottom"],            "top")
_BOTTOM   = cast(Literal["left", "right", "top", "bottom"],            "bottom")
_W        = cast(Literal["n", "s", "e", "w", "ne", "nw", "se", "sw"], "w")
_NORMAL   = cast(Literal["normal", "disabled"],                         "normal")
_DISABLED = cast(Literal["normal", "disabled"],                         "disabled")


def _ui(root: tk.Tk, fn: Callable[[], None]) -> None:
    """Planifie fn() dans le thread Tkinter. Zéro argument → zéro erreur PyCharm."""
    root.after(0, fn)


class TransformView:
    def __init__(self, root: tk.Tk, back: Callable[[], None]) -> None:
        self.root = root
        self.back = back
        self.fichiers: list[Path] = []
        self.traitement_en_cours = False
        self.fenetre_progression: ProgressionWindow | None = None
        self.root.title("Application Comptable - DLM")
        self.root.geometry("750x650")
        self._creer_interface()
        self.rafraichir_liste()

    # ─────────────────────────────────────────────────────────────────────
    def _creer_interface(self) -> None:
        for w in self.root.winfo_children():
            w.destroy()

        # ── HEADER ──────────────────────────────────────────────────────
        frame_header = ttk.Frame(self.root, padding="15 15 15 5")
        frame_header.pack(fill=_X)

        ttk.Button(frame_header, text="← Accueil",
                   command=self.back).pack(side=_LEFT)
        ttk.Label(frame_header,
                  text="📂  Transformation fichiers → Import Compta",
                  style="Title.TLabel").pack(side=_LEFT, padx=15)

        ttk.Separator(self.root, orient="horizontal").pack(fill=_X, padx=15, pady=5)

        # ── CHEMINS ─────────────────────────────────────────────────────
        frame_chemins = ttk.Frame(self.root, padding="15 0")
        frame_chemins.pack(fill=_X)

        ttk.Label(frame_chemins, text="📁 Dossier brut  : ").grid(
            row=0, column=0, sticky=_W)
        ttk.Label(frame_chemins, text=str(DOSSIER_BRUT),
                  foreground="#2980b9").grid(row=0, column=1, sticky=_W)
        ttk.Label(frame_chemins, text="💾 Dossier sortie : ").grid(
            row=1, column=0, sticky=_W)
        ttk.Label(frame_chemins, text=str(DOSSIER_SORTIE),
                  foreground="#2980b9").grid(row=1, column=1, sticky=_W)

        ttk.Separator(self.root, orient="horizontal").pack(fill=_X, padx=15, pady=8)

        # ── BOUTONS ─────────────────────────────────────────────────────
        frame_boutons = ttk.Frame(self.root, padding="15 0")
        frame_boutons.pack(fill=_X)

        ttk.Button(frame_boutons, text="🔄 Rafraîchir",
                   command=self.rafraichir_liste).pack(side=_LEFT, padx=4)

        self.btn_traitement = ttk.Button(
            frame_boutons, text="▶ Lancer le traitement",
            command=self.lancer_traitement)
        self.btn_traitement.pack(side=_LEFT, padx=4)

        ttk.Button(frame_boutons, text="📂 Ouvrir sortie",
                   command=self._ouvrir_dossier_sortie).pack(side=_LEFT, padx=4)
        ttk.Button(frame_boutons, text="🗑 Vider brut",
                   command=self.vider_dossier_brut).pack(side=_LEFT, padx=4)

        ttk.Separator(self.root, orient="horizontal").pack(fill=_X, padx=15, pady=8)

        # ── LISTE FICHIERS ───────────────────────────────────────────────
        frame_liste = ttk.LabelFrame(self.root, text="📋 Fichiers détectés :",
                                     padding="10")
        frame_liste.pack(fill=_BOTH, expand=False, padx=15, pady=5)

        scroll_liste = ttk.Scrollbar(frame_liste)
        scroll_liste.pack(side=_RIGHT, fill=_Y)

        self.liste_fichiers = tk.Listbox(
            frame_liste, height=6,
            yscrollcommand=scroll_liste.set,
            font=("Consolas", 9),
            bg="#ffffff", selectbackground="#2980b9")
        self.liste_fichiers.pack(fill=_BOTH, expand=True)
        scroll_liste.config(command=self.liste_fichiers.yview)

        self.label_statut = ttk.Label(
            self.root, text="⬤  0 fichier(s) détecté(s)",
            foreground="#7f8c8d")
        self.label_statut.pack(pady=3)

        ttk.Separator(self.root, orient="horizontal").pack(fill=_X, padx=15, pady=5)

        # ── LOGS ────────────────────────────────────────────────────────
        frame_logs = ttk.LabelFrame(self.root, text="📝 Logs :", padding="10")
        frame_logs.pack(fill=_BOTH, expand=True, padx=15, pady=5)

        scroll_log = ttk.Scrollbar(frame_logs)
        scroll_log.pack(side=_RIGHT, fill=_Y)

        self.zone_log = tk.Text(
            frame_logs,
            yscrollcommand=scroll_log.set,
            font=("Consolas", 9),
            bg="#1e1e2e", fg="#cdd6f4",
            state=_DISABLED)
        self.zone_log.pack(fill=_BOTH, expand=True)
        scroll_log.config(command=self.zone_log.yview)

        self.zone_log.tag_config("INFO",    foreground="#89b4fa")
        self.zone_log.tag_config("SUCCESS", foreground="#a6e3a1")
        self.zone_log.tag_config("WARNING", foreground="#f9e2af")
        self.zone_log.tag_config("ERROR",   foreground="#f38ba8")
        self.zone_log.tag_config("DEBUG",   foreground="#6c7086")

        # ── FOOTER ──────────────────────────────────────────────────────
        frame_footer = ttk.Frame(self.root, padding="5")
        frame_footer.pack(fill=_X, side=_BOTTOM)

        ttk.Button(frame_footer, text="🧹 Vider les logs",
                   command=self.vider_logs).pack()
        ttk.Label(
            frame_footer,
            text="Cree par Matthias C.",
            foreground="#95a5a6",
            font=("Segoe UI", 8),
        ).pack(pady=2)

    # ─────────────────────────────────────────────────────────────────────
    def ajouter_log(self, message: str, niveau: str = "INFO") -> None:
        heure = datetime.datetime.now().strftime("%H:%M:%S")
        self.zone_log.config(state=_NORMAL)
        self.zone_log.insert(tk.END, f"{heure} {message}\n", niveau)
        self.zone_log.see(tk.END)
        self.zone_log.config(state=_DISABLED)

    def vider_logs(self) -> None:
        self.zone_log.config(state=_NORMAL)
        self.zone_log.delete("1.0", tk.END)
        self.zone_log.config(state=_DISABLED)

    # ─────────────────────────────────────────────────────────────────────
    def rafraichir_liste(self) -> None:
        fichiers = [
            f for f in DOSSIER_BRUT.glob("*.*")
            if f.suffix.lower() in (".xlsx", ".xls", ".csv")
        ]
        self.fichiers = [
            f for f in fichiers
            if not (f.suffix.lower() == ".xlsx" and f.with_suffix(".xls").exists())
        ]

        self.liste_fichiers.delete(0, tk.END)
        for f in self.fichiers:
            self.liste_fichiers.insert(tk.END, f"  📄 {f.name}")

        nb = len(self.fichiers)
        self.label_statut.config(
            text=f"⬤  {nb} fichier(s) détecté(s)",
            foreground="#27ae60" if nb > 0 else "#7f8c8d")
        self.ajouter_log(f"Liste rafraîchie : {nb} fichiers Module 1", "DEBUG")
        logger.debug("Liste rafraîchie : %d fichiers Module 1", nb)

    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def _ouvrir_dossier_sortie() -> None:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(DOSSIER_SORTIE)])
        else:
            subprocess.Popen(["xdg-open", str(DOSSIER_SORTIE)])

    # ─────────────────────────────────────────────────────────────────────
    def vider_dossier_brut(self) -> None:
        if not messagebox.askyesno("Confirmation", "Vider le dossier brut ?"):
            return
        for f in DOSSIER_BRUT.glob("*.*"):
            try:
                f.unlink()
                self.ajouter_log(f"Supprime : {f.name}", "WARNING")
            except OSError as exc:
                self.ajouter_log(f"Erreur suppression {f.name} : {exc}", "ERROR")
        self.rafraichir_liste()

    # ─────────────────────────────────────────────────────────────────────
    def lancer_traitement(self) -> None:
        if self.traitement_en_cours:
            return
        if not self.fichiers:
            messagebox.showwarning("Attention", "Aucun fichier à traiter.")
            return

        self.traitement_en_cours = True
        self.btn_traitement.config(state=_DISABLED)
        self.label_statut.config(text="⬤  Traitement en cours...",
                                 foreground="#e67e22")
        self.fenetre_progression = ProgressionWindow(self.root, len(self.fichiers))
        threading.Thread(target=self.executer_traitement, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────
    def executer_traitement(self) -> None:
        succes = erreurs = partiels = 0
        _ui(self.root, lambda: self.ajouter_log(
            "=== DEBUT DU TRAITEMENT MODULE 1 ===", "INFO"))
        logger.info("=== DEBUT DU TRAITEMENT MODULE 1 ===")

        for i, fichier in enumerate(self.fichiers, 1):
            # ── Progression ─────────────────────────────────────────────
            if self.fenetre_progression:
                _fp, _i, _n = self.fenetre_progression, i, fichier.name
                _ui(self.root, lambda fp=_fp, idx=_i, n=_n: fp.maj(idx, n))

            try:
                resultat = traiter_fichier(fichier)

                # ── Normalisation : tuple ("OK", path) ou dict {"statut":...} ──
                if isinstance(resultat, tuple):
                    statut = resultat[0]
                    detail = str(resultat[1]) if len(resultat) > 1 else ""
                    message = ""
                elif isinstance(resultat, dict):
                    statut = resultat.get("statut", "ERREUR")
                    detail = resultat.get("fichier", "")
                    message = resultat.get("message", "")
                else:
                    statut = "ERREUR"
                    detail = f"Type de retour inattendu : {type(resultat)}"
                    message = ""

                nom = fichier.name

                # ── Routing statut ───────────────────────────────────────
                # Handlers Module 1 retournent "OK"
                # Anciens handlers peuvent retourner "SUCCES"
                if statut in ("OK", "SUCCES"):
                    succes += 1
                    _ui(self.root, lambda n=nom, d=detail: self.ajouter_log(
                        f"✅ {n}" + (f" → {Path(d).name}" if d else ""), "SUCCESS"))
                    logger.info("✅ %s traite avec succes", nom)

                elif statut == "PARTIEL":
                    partiels += 1
                    _ui(self.root, lambda n=nom, d=detail: self.ajouter_log(
                        f"⚠ {n} : traitement partiel" + (f" — {d}" if d else ""),
                        "WARNING"))
                    logger.warning("⚠ %s traite partiellement", nom)

                elif statut == "AUCUN_HANDLER":
                    erreurs += 1
                    _ui(self.root, lambda n=nom: self.ajouter_log(
                        f"⚠ {n} : aucun handler detecte", "WARNING"))
                    logger.warning("⚠ Aucun handler detecte pour %s", nom)

                else:
                    # ERREUR ou statut inconnu
                    erreurs += 1
                    msg = message or detail or statut
                    _ui(self.root, lambda n=nom, m=msg: self.ajouter_log(
                        f"❌ {n} : {m}", "ERROR"))
                    logger.error("❌ Erreur %s : %s", nom, msg)

            except OSError as exc:
                erreurs += 1
                nom_exc = fichier.name
                err_exc = str(exc)
                _ui(self.root, lambda n=nom_exc, er=err_exc: self.ajouter_log(
                    f"❌ {n} : {er}", "ERROR"))
                logger.error("❌ OSError %s : %s", fichier.name, exc)

            except Exception as exc:
                # Filet de sécurité — ne jamais laisser le thread mourir silencieusement
                erreurs += 1
                nom_exc = fichier.name
                err_exc = str(exc)
                _ui(self.root, lambda n=nom_exc, er=err_exc: self.ajouter_log(
                    f"❌ {n} : {er}", "ERROR"))
                logger.error("❌ Exception inattendue %s : %s", fichier.name, exc,
                             exc_info=True)

        logger.info("Succes : %d | Partiels : %d | Erreurs : %d",
                    succes, partiels, erreurs)

        # ── Fermeture progression ────────────────────────────────────────
        if self.fenetre_progression:
            _fp = self.fenetre_progression
            _ui(self.root, lambda fp=_fp: fp.fermer())

        # ── Affichage résultats ──────────────────────────────────────────
        _s, _e, _p = succes, erreurs, partiels
        _ui(self.root, lambda s=_s, er=_e, p=_p: self.afficher_resultats(s, er, p))

    # ─────────────────────────────────────────────────────────────────────
    def afficher_resultats(self, succes: int, erreurs: int, partiels: int = 0) -> None:
        self.traitement_en_cours = False
        self.btn_traitement.config(state=_NORMAL)
        self.label_statut.config(text="⬤  Traitement termine",
                                 foreground="#2980b9")

        niveau = "SUCCESS" if erreurs == 0 and partiels == 0 else "WARNING"
        self.ajouter_log(
            f"=== FIN : ✅ {succes} succes | ⚠ {partiels} partiels"
            f" | ❌ {erreurs} erreurs ===",
            niveau,
        )
        messagebox.showinfo(
            "Resultat",
            f"✅ Succes : {succes}\n⚠ Partiels : {partiels}\n❌ Erreurs : {erreurs}",
        )
        self.rafraichir_liste()
