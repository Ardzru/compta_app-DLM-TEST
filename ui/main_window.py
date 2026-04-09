import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

from config import DOSSIER_BRUT, DOSSIER_SORTIE
from logger import logger
from core.dispatcher import traiter_fichier
from ui.log_viewer import LogViewer
from ui.progression import ProgressionWindow

_log = logging.getLogger("ui.main_window")


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Application Comptable - SERMA")
        self.root.geometry("700x600")
        self.root.resizable(False, False)

        self.fichiers = []
        self.traitement_en_cours = False

        self._creer_interface()   # ← construit tout
        self.rafraichir_liste()

    # ─────────────────────────────────────────────────────────────────────
    def _creer_interface(self):

        # ── Titre ────────────────────────────────────────────────────────
        ttk.Label(self.root, text="Application Comptable SERMA",
                  font=("Arial", 16, "bold")).pack(pady=10)

        # ── Infos dossiers ───────────────────────────────────────────────
        frame_info = ttk.Frame(self.root, padding="5")
        frame_info.pack(fill=tk.X)
        ttk.Label(frame_info, text=f"Dossier brut   : {DOSSIER_BRUT}").pack(anchor="w")
        ttk.Label(frame_info, text=f"Dossier sortie : {DOSSIER_SORTIE}").pack(anchor="w")

        # ── Boutons ──────────────────────────────────────────────────────
        frame_boutons = ttk.Frame(self.root)
        frame_boutons.pack(pady=5)

        ttk.Button(frame_boutons, text="🔄 Rafraîchir",
                   command=self.rafraichir_liste).grid(row=0, column=0, padx=5)

        self.btn_traitement = ttk.Button(frame_boutons, text="▶ Lancer le traitement",
                                          command=self.lancer_traitement)
        self.btn_traitement.grid(row=0, column=1, padx=5)

        ttk.Button(frame_boutons, text="📂 Ouvrir dossier sortie",
                   command=self.ouvrir_dossier_sortie).grid(row=0, column=2, padx=5)

        ttk.Button(frame_boutons, text="🗑️ Vider dossier brut",
                   command=self.vider_dossier_brut).grid(row=0, column=3, padx=5)

        # ── Liste fichiers ───────────────────────────────────────────────
        ttk.Label(self.root, text="Fichiers détectés :").pack(anchor="w", padx=15)

        frame_liste = ttk.Frame(self.root, padding="5")
        frame_liste.pack(fill=tk.X, padx=10)

        scroll_liste = ttk.Scrollbar(frame_liste, orient=tk.VERTICAL)
        self.liste_fichiers = tk.Listbox(frame_liste, height=6, width=80,
                                          yscrollcommand=scroll_liste.set)
        scroll_liste.config(command=self.liste_fichiers.yview)
        self.liste_fichiers.pack(side=tk.LEFT)
        scroll_liste.pack(side=tk.LEFT, fill=tk.Y)

        # ── Statut ───────────────────────────────────────────────────────
        self.label_statut = ttk.Label(self.root, text="Prêt",
                                       foreground="green")
        self.label_statut.pack(pady=3)

        # ── Zone logs ────────────────────────────────────────────────────
        ttk.Label(self.root, text="Logs :").pack(anchor="w", padx=15)

        frame_logs = ttk.Frame(self.root, padding="5")
        frame_logs.pack(fill=tk.BOTH, expand=True, padx=10)

        scroll_logs = ttk.Scrollbar(frame_logs, orient=tk.VERTICAL)
        self.zone_logs = LogViewer(frame_logs, height=8, width=80,
                                    yscrollcommand=scroll_logs.set)
        scroll_logs.config(command=self.zone_logs.yview)
        self.zone_logs.pack(side=tk.LEFT)
        scroll_logs.pack(side=tk.LEFT, fill=tk.Y)

        # ── Bouton vider logs ────────────────────────────────────────────
        ttk.Button(self.root, text="🧹 Vider les logs",
                   command=self.zone_logs.vider).pack(pady=3)

    # ─────────────────────────────────────────────────────────────────────
    def ajouter_log(self, message: str, niveau: str = "INFO"):
        self.zone_logs.ajouter(message, niveau)

    # ─────────────────────────────────────────────────────────────────────
    def rafraichir_liste(self):
        self.fichiers = sorted(DOSSIER_BRUT.glob("*.*"))
        self.liste_fichiers.delete(0, tk.END)
        for f in self.fichiers:
            self.liste_fichiers.insert(tk.END, f.name)
        self.label_statut.config(
            text=f"{len(self.fichiers)} fichier(s) détecté(s)",
            foreground="green"
        )
        self.ajouter_log(f"{len(self.fichiers)} fichier(s) détecté(s)", "INFO")
        _log.debug(f"Liste rafraîchie : {len(self.fichiers)} fichiers")

    # ─────────────────────────────────────────────────────────────────────
    def ouvrir_dossier_sortie(self):
        if os.name == "nt":
            os.startfile(DOSSIER_SORTIE)
        else:
            subprocess.Popen(["xdg-open", str(DOSSIER_SORTIE)])

    # ─────────────────────────────────────────────────────────────────────
    def vider_dossier_brut(self):
        if not messagebox.askyesno("Confirmation",
                                    "Vider le dossier brut ?"):
            return
        for f in DOSSIER_BRUT.glob("*.*"):
            try:
                f.unlink()
                self.ajouter_log(f"Supprimé : {f.name}", "WARNING")
            except Exception as e:
                self.ajouter_log(f"Erreur suppression {f.name} : {e}", "ERROR")
        self.rafraichir_liste()

    # ─────────────────────────────────────────────────────────────────────
    def lancer_traitement(self):
        if self.traitement_en_cours:
            return
        if not self.fichiers:
            messagebox.showwarning("Attention", "Aucun fichier à traiter.")
            return

        self.traitement_en_cours = True
        self.btn_traitement.config(state=tk.DISABLED)
        self.label_statut.config(text="Traitement en cours...",
                                  foreground="orange")

        self.fenetre_progression = ProgressionWindow(self.root, len(self.fichiers))
        threading.Thread(target=self.executer_traitement, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────
    def executer_traitement(self):
        succes = 0
        erreurs = 0
        self.ajouter_log("=== DÉBUT DU TRAITEMENT ===", "INFO")
        logger.info("=== DÉBUT DU TRAITEMENT ===")

        for i, fichier in enumerate(self.fichiers, 1):
            self.root.after(0, self.fenetre_progression.maj, i, fichier.name)
            try:
                traiter_fichier(fichier)
                succes += 1
                self.root.after(0, self.ajouter_log,
                                f"✅ {fichier.name}", "SUCCESS")
                logger.info(f"✅ {fichier.name} traité avec succès")
            except Exception as e:
                erreurs += 1
                self.root.after(0, self.ajouter_log,
                                f"❌ {fichier.name} : {e}", "ERROR")
                logger.error(f"❌ Erreur sur {fichier.name} : {e}")

        logger.info(f"Succès : {succes} | Erreurs : {erreurs}")
        self.root.after(0, self.fenetre_progression.fermer)
        self.root.after(0, self.afficher_resultats, succes, erreurs)

    # ─────────────────────────────────────────────────────────────────────
    def afficher_resultats(self, succes, erreurs):
        self.traitement_en_cours = False
        self.btn_traitement.config(state=tk.NORMAL)
        self.label_statut.config(text="Traitement terminé", foreground="blue")
        self.ajouter_log(f"=== FIN : ✅ {succes} succès | ❌ {erreurs} erreurs ===",
                          "SUCCESS" if erreurs == 0 else "WARNING")
        messagebox.showinfo("Résultat",
                             f"✅ Succès : {succes}\n❌ Erreurs : {erreurs}")
        self.rafraichir_liste()
