import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys

from config import DOSSIER_BRUT, DOSSIER_SORTIE
from core.dispatcher import traiter_fichier
from ui.progression import ProgressionWindow

logger = logging.getLogger("ui.transform_view")

class TransformView:
    def __init__(self, root: tk.Tk, back):
        self.root = root
        self.back = back
        self.fichiers = []
        self.traitement_en_cours = False
        self.root.title("Application Comptable - DLM")
        self.root.geometry("750x650")
        self._creer_interface()
        self.rafraichir_liste()

    # ─────────────────────────────────────────────────────────────────────
    def _creer_interface(self):
        for w in self.root.winfo_children():
            w.destroy()

        # ── HEADER ──────────────────────────────────────────────────────
        frame_header = ttk.Frame(self.root, padding="15 15 15 5")
        frame_header.pack(fill=tk.X)

        ttk.Button(frame_header, text="← Accueil",
                   command=self.back).pack(side=tk.LEFT)

        ttk.Label(frame_header,
                  text="📂  Transformation fichiers → Import Compta",
                  style="Title.TLabel").pack(side=tk.LEFT, padx=15)

        ttk.Separator(self.root, orient="horizontal").pack(fill=tk.X,
                                                            padx=15, pady=5)

        # ── CHEMINS ─────────────────────────────────────────────────────
        frame_chemins = ttk.Frame(self.root, padding="15 0")
        frame_chemins.pack(fill=tk.X)

        ttk.Label(frame_chemins, text="📁 Dossier brut  : ").grid(
            row=0, column=0, sticky=tk.W)
        ttk.Label(frame_chemins, text=str(DOSSIER_BRUT),
                  foreground="#2980b9").grid(row=0, column=1, sticky=tk.W)

        ttk.Label(frame_chemins, text="💾 Dossier sortie : ").grid(
            row=1, column=0, sticky=tk.W)
        ttk.Label(frame_chemins, text=str(DOSSIER_SORTIE),
                  foreground="#2980b9").grid(row=1, column=1, sticky=tk.W)

        ttk.Separator(self.root, orient="horizontal").pack(fill=tk.X,
                                                            padx=15, pady=8)

        # ── BOUTONS ─────────────────────────────────────────────────────
        frame_boutons = ttk.Frame(self.root, padding="15 0")
        frame_boutons.pack(fill=tk.X)

        ttk.Button(frame_boutons, text="🔄 Rafraîchir",
                   command=self.rafraichir_liste).pack(side=tk.LEFT, padx=4)

        self.btn_traitement = ttk.Button(
            frame_boutons, text="▶ Lancer le traitement",
            command=self.lancer_traitement)
        self.btn_traitement.pack(side=tk.LEFT, padx=4)

        ttk.Button(frame_boutons, text="📂 Ouvrir sortie",
                   command=self.ouvrir_dossier_sortie).pack(side=tk.LEFT, padx=4)

        ttk.Button(frame_boutons, text="🗑 Vider brut",
                   command=self.vider_dossier_brut).pack(side=tk.LEFT, padx=4)

        ttk.Separator(self.root, orient="horizontal").pack(fill=tk.X,
                                                            padx=15, pady=8)

        # ── LISTE FICHIERS ───────────────────────────────────────────────
        frame_liste = ttk.LabelFrame(self.root, text="📋 Fichiers détectés :",
                                     padding="10")
        frame_liste.pack(fill=tk.BOTH, expand=False, padx=15, pady=5)

        scroll_liste = ttk.Scrollbar(frame_liste)
        scroll_liste.pack(side=tk.RIGHT, fill=tk.Y)

        self.liste_fichiers = tk.Listbox(
            frame_liste, height=6,
            yscrollcommand=scroll_liste.set,
            font=("Consolas", 9),
            bg="#ffffff", selectbackground="#2980b9")
        self.liste_fichiers.pack(fill=tk.BOTH, expand=True)
        scroll_liste.config(command=self.liste_fichiers.yview)

        self.label_statut = ttk.Label(
            self.root, text="⬤  0 fichier(s) détecté(s)",
            foreground="#7f8c8d")
        self.label_statut.pack(pady=3)

        ttk.Separator(self.root, orient="horizontal").pack(fill=tk.X,
                                                            padx=15, pady=5)

        # ── LOGS ────────────────────────────────────────────────────────
        frame_logs = ttk.LabelFrame(self.root, text="📝 Logs :", padding="10")
        frame_logs.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        scroll_log = ttk.Scrollbar(frame_logs)
        scroll_log.pack(side=tk.RIGHT, fill=tk.Y)

        self.zone_log = tk.Text(
            frame_logs,
            yscrollcommand=scroll_log.set,
            font=("Consolas", 9),
            bg="#1e1e2e", fg="#cdd6f4",
            state=tk.DISABLED)
        self.zone_log.pack(fill=tk.BOTH, expand=True)
        scroll_log.config(command=self.zone_log.yview)

        self.zone_log.tag_config("INFO",    foreground="#89b4fa")
        self.zone_log.tag_config("SUCCESS", foreground="#a6e3a1")
        self.zone_log.tag_config("WARNING", foreground="#f9e2af")
        self.zone_log.tag_config("ERROR",   foreground="#f38ba8")
        self.zone_log.tag_config("DEBUG",   foreground="#6c7086")

        # ── FOOTER ──────────────────────────────────────────────────────
        frame_footer = ttk.Frame(self.root, padding="5")
        frame_footer.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(frame_footer, text="🧹 Vider les logs",
                   command=self.vider_logs).pack()

        ttk.Label(frame_footer, text="Créé par Matthias Carvalho",
                  foreground="#95a5a6",
                  font=("Segoe UI", 8)).pack(pady=2)

    # ─────────────────────────────────────────────────────────────────────
    def ajouter_log(self, message: str, niveau: str = "INFO"):
        import datetime
        heure = datetime.datetime.now().strftime("%H:%M:%S")
        self.zone_log.config(state=tk.NORMAL)
        self.zone_log.insert(tk.END, f"{heure} {message}\n", niveau)
        self.zone_log.see(tk.END)
        self.zone_log.config(state=tk.DISABLED)

    def vider_logs(self):
        self.zone_log.config(state=tk.NORMAL)
        self.zone_log.delete("1.0", tk.END)
        self.zone_log.config(state=tk.DISABLED)

    # ─────────────────────────────────────────────────────────────────────
    def rafraichir_liste(self):
        self.fichiers = [
            f for f in DOSSIER_BRUT.glob("*.*")
            if f.suffix.lower() in (".xlsx", ".xls", ".csv", ".pdf")
        ]
        self.liste_fichiers.delete(0, tk.END)
        for f in self.fichiers:
            self.liste_fichiers.insert(tk.END, f"  📄 {f.name}")

        nb = len(self.fichiers)
        couleur = "#27ae60" if nb > 0 else "#7f8c8d"
        self.label_statut.config(
            text=f"⬤  {nb} fichier(s) détecté(s)",
            foreground=couleur)
        self.ajouter_log(f"Liste rafraîchie : {nb} fichiers", "DEBUG")
        logger.debug(f"Liste rafraîchie : {nb} fichiers")

    # ─────────────────────────────────────────────────────────────────────
    def ouvrir_dossier_sortie(self):
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(DOSSIER_SORTIE)])
        else:
            subprocess.Popen(["xdg-open", str(DOSSIER_SORTIE)])

    # ─────────────────────────────────────────────────────────────────────
    def vider_dossier_brut(self):
        if not messagebox.askyesno("Confirmation", "Vider le dossier brut ?"):
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
        self.label_statut.config(text="⬤  Traitement en cours...",
                                  foreground="#e67e22")

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
                self.root.after(0, self.ajouter_log, f"✅ {fichier.name}", "SUCCESS")
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
        self.label_statut.config(text="⬤  Traitement terminé",
                                  foreground="#2980b9")
        self.ajouter_log(
            f"=== FIN : ✅ {succes} succès | ❌ {erreurs} erreurs ===",
            "SUCCESS" if erreurs == 0 else "WARNING"
        )
        messagebox.showinfo("Résultat",
                            f"✅ Succès : {succes}\n❌ Erreurs : {erreurs}")
        self.rafraichir_liste()
