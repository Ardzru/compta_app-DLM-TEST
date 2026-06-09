import sys
import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

# ── Répertoire de base ────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

log_file = BASE_DIR / "compta_app.log"

# ── Logger bootstrap app.py uniquement ───────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
_log = logging.getLogger("app")


def show_fatal_error(msg: str) -> None:
    """Affiche un message d'erreur ET écrit dans le log."""  # ✅ :31 "un message" accord masculin
    _log.critical(msg)
    try:
        _root = tk.Tk()
        _root.withdraw()
        messagebox.showerror("Erreur fatale – ComptaApp", msg)
        _root.destroy()
    except Exception as _err:
        _log.debug(f"show_fatal_error UI indisponible : {_err}")


# ── Démarrage ─────────────────────────────────────────────────────────────────
_log.debug("=" * 60)
_log.debug("=== DÉMARRAGE app.py ===")
_log.debug(f"Python     : {sys.version}")
_log.debug(f"Executable : {sys.executable}")
_log.debug(f"Frozen     : {getattr(sys, 'frozen', False)}")
_log.debug(f"BASE_DIR   : {BASE_DIR}")
_log.debug(f"Log file   : {log_file}")

# ── 1. Config ─────────────────────────────────────────────────────────────────
_log.debug("Import config...")
try:
    from config import DOSSIER_BRUT, DOSSIER_SORTIE, logger
    _log.debug(f"DOSSIER_BRUT   = {DOSSIER_BRUT}")
    _log.debug(f"DOSSIER_SORTIE = {DOSSIER_SORTIE}")
    _log.debug("logger OK")
except Exception as exc:
    show_fatal_error(f"Echec import config :\n{exc}")
    sys.exit(1)

# ── 2. MainWindow ─────────────────────────────────────────────────────────────
_log.debug("Import MainWindow...")
try:
    from ui.main_window import MainWindow
    _log.debug("MainWindow OK")
except Exception as exc:
    show_fatal_error(f"Echec import MainWindow :\n{exc}")
    sys.exit(1)

# ── 3. Kiosque auto (optionnel) ───────────────────────────────────────────────
_log.debug("Initialisation kiosque auto...")
try:
    from modules.module_3.auto_kiosque import generer_ligne_kiosque_auto
    if generer_ligne_kiosque_auto():
        _log.info("Ligne kiosque auto créée")
    else:
        _log.debug("Kiosque auto déjà existant pour aujourd'hui")
except Exception as exc:
    _log.warning(f"Kiosque auto non disponible : {exc}")

# ── 4. Dispatcher (validation import) ────────────────────────────────────────
_log.debug("Import dispatcher...")
try:
    from core.dispatcher import traiter_fichier  # noqa: F401
    _log.debug("dispatcher OK")
except Exception as exc:
    show_fatal_error(f"Echec import dispatcher :\n{exc}")
    sys.exit(1)

_log.debug("Tous les imports OK — lancement interface")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    """Point d'entrée principal de l'application."""
    _log.debug("main() appelé")
    try:
        root = tk.Tk()
        _log.debug("Tk() créé")
        MainWindow(root)         # ✅ :98 suppression commentaire (évite accord + shadow)
        _log.debug("Lancement mainloop")
        root.mainloop()
        _log.debug("mainloop terminée proprement")
    except Exception as err:     # ✅ :102 renommé "err" → plus de shadow sur "exc" module-level
        _log.critical(f"Erreur fatale dans main() : {err}", exc_info=True)
        show_fatal_error(
            f"L'application a planté :\n{err}\n\nVoir le log :\n{log_file}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
