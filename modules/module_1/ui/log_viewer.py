import tkinter as tk
import logging
from typing import Literal

_log = logging.getLogger("ui.log_viewer")

# ── Constantes typées ─────────────────────────────────────────────────────────
_NORMAL:   Literal["normal", "disabled"] = "normal"
_DISABLED: Literal["normal", "disabled"] = "disabled"
_WORD:     Literal["none", "char", "word"] = "word"


class LogViewer(tk.Text):
    """Widget Text enrichi pour afficher les logs en temps réel."""

    COULEURS = {
        "DEBUG":    {"fg": "#888888"},
        "INFO":     {"fg": "#d4d4d4"},
        "SUCCESS":  {"fg": "#4ec94e"},
        "WARNING":  {"fg": "#f0a500"},
        "ERROR":    {"fg": "#f44747"},
        "CRITICAL": {"fg": "#ff0000"},
    }

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(
            parent,
            state=_DISABLED,    # ✅ Literal
            bg="#1e1e1e",
            fg="#d4d4d4",
            font=("Consolas", 9),
            wrap=_WORD,         # ✅ Literal
            **kwargs
        )
        self._configurer_tags()
        self._connecter_logger()

    def _configurer_tags(self) -> None:
        for niveau, style in self.COULEURS.items():
            self.tag_config(niveau, foreground=style["fg"])

    def _connecter_logger(self) -> None:
        """Branche un handler sur le logger racine."""
        handler = _LogViewerHandler(self)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s : %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)

    def ajouter(self, message: str, niveau: str = "INFO") -> None:
        """Ajoute une ligne avec la couleur du niveau."""
        niveau = niveau.upper()
        if niveau not in self.COULEURS:
            niveau = "INFO"

        self.config(state=_NORMAL)    # ✅ Literal
        self.insert(tk.END, message + "\n", niveau)
        self.see(tk.END)
        self.config(state=_DISABLED)  # ✅ Literal

    def vider(self) -> None:
        """Efface tout le contenu."""
        self.config(state=_NORMAL)    # ✅ Literal
        self.delete("1.0", tk.END)
        self.config(state=_DISABLED)  # ✅ Literal


class _LogViewerHandler(logging.Handler):
    """Handler logging qui redirige vers le LogViewer."""

    NIVEAUX = {
        "DEBUG":    "DEBUG",
        "INFO":     "INFO",
        "WARNING":  "WARNING",
        "ERROR":    "ERROR",
        "CRITICAL": "CRITICAL",
    }

    def __init__(self, viewer: LogViewer) -> None:
        super().__init__()
        self.viewer = viewer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            niveau = self.NIVEAUX.get(record.levelname, "INFO")
            self.viewer.after(0, self.viewer.ajouter, msg, niveau)
        except (RuntimeError, tk.TclError):  # ✅ widget détruit ou thread mort
            self.handleError(record)

