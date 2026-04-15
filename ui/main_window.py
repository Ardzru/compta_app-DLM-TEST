import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger("ui.main_window")

class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Application Comptable - DLM")
        self.root.geometry("480x320")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f2f5")
        self._style()
        self._build_home()

    # ─────────────────────────────────────────────────────────────────────
    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame",      background="#f0f2f5")
        s.configure("TLabel",      background="#f0f2f5",
                    font=("Segoe UI", 10))
        s.configure("Title.TLabel", background="#f0f2f5",
                    font=("Segoe UI", 14, "bold"), foreground="#1a1a2e")
        s.configure("Sub.TLabel",  background="#f0f2f5",
                    font=("Segoe UI", 9),  foreground="#555555")
        s.configure("Big.TButton", font=("Segoe UI", 11, "bold"), padding=14)

    # ─────────────────────────────────────────────────────────────────────
    def _build_home(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.root.geometry("480x320")
        self.root.resizable(False, False)

        frame = ttk.Frame(self.root, padding="30 20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="🧾 Application Comptable DLM",
                  style="Title.TLabel").pack(pady=(0, 4))
        ttk.Label(frame, text="Choisissez un module :",
                  style="Sub.TLabel").pack()
        ttk.Separator(frame, orient="horizontal").pack(fill=tk.X, pady=12)

        ttk.Button(
            frame,
            text="📂  Transformation fichiers → Import Compta",
            style="Big.TButton",
            command=self._ouvrir_transform
        ).pack(fill=tk.X, pady=6)

        ttk.Button(
            frame,
            text="🔍  Justification compte Internet",
            style="Big.TButton",
            command=self._ouvrir_justification
        ).pack(fill=tk.X, pady=6)

        ttk.Separator(frame, orient="horizontal").pack(fill=tk.X, pady=12)
        ttk.Label(frame, text="Créé par Matthias Carvalho",
                  style="Sub.TLabel").pack()

    # ─────────────────────────────────────────────────────────────────────
    def _ouvrir_transform(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.root.resizable(True, True)
        self.root.geometry("750x650")
        from ui.transform_view import TransformView
        TransformView(self.root, self._build_home)

    # ─────────────────────────────────────────────────────────────────────
    def _ouvrir_justification(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.root.resizable(True, True)
        self.root.geometry("750x650")
        from ui.justification_view import JustificationView
        JustificationView(self.root, self._build_home)
