import tkinter as tk
from tkinter import ttk


class ProgressionWindow:
    def __init__(self, parent, total: int):
        self.total = total

        self.win = tk.Toplevel(parent)
        self.win.title("Traitement en cours...")
        self.win.geometry("420x130")
        self.win.resizable(False, False)
        self.win.grab_set()

        frame = ttk.Frame(self.win, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)

        self.label_fichier = ttk.Label(frame, text="Initialisation...", width=50)
        self.label_fichier.pack(pady=5)

        self.barre = ttk.Progressbar(frame, length=370,
                                      mode="determinate", maximum=total)
        self.barre.pack(pady=5)

        self.label_compteur = ttk.Label(frame, text=f"0 / {total}")
        self.label_compteur.pack()

    def maj(self, valeur: int, nom_fichier: str):
        self.label_fichier.config(text=nom_fichier)
        self.barre.config(value=valeur)
        self.label_compteur.config(text=f"{valeur} / {self.total}")

    def fermer(self):
        self.win.destroy()
