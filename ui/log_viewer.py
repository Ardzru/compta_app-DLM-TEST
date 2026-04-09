import tkinter as tk
from tkinter import ttk
import logging

_log = logging.getLogger("ui.log_viewer")


class LogViewer(tk.Text):
    """
    Widget Text enrichi pour afficher les logs en temps réel
    avec coloration par niveau.
    """

    COULEURS = {
        "DEBUG":    {"fg": "#888888"},
        "INFO":     {"fg": "#d4d4d4"},
        "SUCCESS":  {"fg": "#4ec94e"},
        "WARNING":  {"fg": "#f0a500"},
        "ERROR":    {"fg": "#f44747"},
        "CRITICAL": {"fg": "#ff0000"},
    }

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            state=tk.DISABLED,
            bg="#1e1e1e",
            fg="#d4d4d4",
            font=("Consolas", 9),
            wrap=tk.WORD,
            **kwargs
        )
        self._configurer_tags()
        self._connecter_logger()     # ← branche le handler

    def _configurer_tags(self):
        for niveau, style in self.COULEURS.items():
            self.tag_config(niveau, foreground=style["fg"])

    def _connecter_logger(self):
        """Branche un handler sur le logger racine pour capturer tous les logs."""
        handler = _LogViewerHandler(self)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s : %(message)s",
                                       datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)   # ← logger racine = tout capture

    def ajouter(self, message: str, niveau: str = "INFO"):
        """Ajoute une ligne avec la couleur du niveau."""
        niveau = niveau.upper()
        if niveau not in self.COULEURS:
            niveau = "INFO"

        self.config(state=tk.NORMAL)
        self.insert(tk.END, message + "\n", niveau)
        self.see(tk.END)
        self.config(state=tk.DISABLED)

    def vider(self):
        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self.config(state=tk.DISABLED)


class _LogViewerHandler(logging.Handler):
    """Handler logging qui redirige vers le LogViewer."""

    # Correspondance niveau logging → tag couleur
    NIVEAUX = {
        "DEBUG":    "DEBUG",
        "INFO":     "INFO",
        "WARNING":  "WARNING",
        "ERROR":    "ERROR",
        "CRITICAL": "CRITICAL",
    }

    def __init__(self, viewer: LogViewer):
        super().__init__()
        self.viewer = viewer

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            niveau = self.NIVEAUX.get(record.levelname, "INFO")

            # Toujours appeler depuis le thread principal Tkinter
            self.viewer.after(0, self.viewer.ajouter, msg, niveau)
        except Exception:
            self.handleError(record)
