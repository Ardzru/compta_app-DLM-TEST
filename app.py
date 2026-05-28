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

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
_log = logging.getLogger("app")

def show_fatal_error(msg: str):
    """Affiche une popup d'erreur ET écrit dans le log."""
    _log.critical(msg)
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erreur fatale – ComptaApp", msg)
        root.destroy()
    except Exception:
        pass

# ── Démarrage ─────────────────────────────────────────────────────────────────
_log.debug("=" * 60)
_log.debug("=== DÉMARRAGE app.py ===")
_log.debug(f"Python     : {sys.version}")
_log.debug(f"Executable : {sys.executable}")
_log.debug(f"Frozen     : {getattr(sys, 'frozen', False)}")
_log.debug(f"BASE_DIR   : {BASE_DIR}")
_log.debug(f"Log file   : {log_file}")

# ── Imports projet ────────────────────────────────────────────────────────────
_log.debug("Initialisation kiosque auto...")
try:
    from modules.module_3.auto_kiosque import generer_ligne_kiosque_auto
    if generer_ligne_kiosque_auto():
        _log.info("✅ Ligne kiosque auto créée")
    else:
        _log.debug("✓ Kiosque auto déjà existant pour aujourd'hui")
except Exception as e:
    _log.warning(f"⚠️ Kiosque auto non disponible : {e}")

_log.debug("Import config...")
try:
    from config import DOSSIER_BRUT, DOSSIER_SORTIE
    _log.debug(f"DOSSIER_BRUT   = {DOSSIER_BRUT}")
    _log.debug(f"DOSSIER_SORTIE = {DOSSIER_SORTIE}")
except Exception as e:
    show_fatal_error(f"Echec import config :\n{e}")
    sys.exit(1)

_log.debug("Import logger...")
try:
    from config import logger
    _log.debug("logger OK")
except Exception as e:
    show_fatal_error(f"Echec import logger :\n{e}")
    sys.exit(1)

_log.debug("Import dispatcher...")
try:
    from core.dispatcher import traiter_fichier
    _log.debug("dispatcher OK")
except Exception as e:
    show_fatal_error(f"Echec import dispatcher :\n{e}")
    sys.exit(1)

_log.debug("Import MainWindow...")
try:
    from ui.main_window import MainWindow
    _log.debug("MainWindow OK")
except Exception as e:
    show_fatal_error(f"Echec import MainWindow :\n{e}")
    sys.exit(1)

_log.debug("Tous les imports OK")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    _log.debug("main() appelé")
    try:
        root = tk.Tk()
        _log.debug("Tk() créé")
        app = MainWindow(root)
        _log.debug("Lancement mainloop")
        root.mainloop()
        _log.debug("mainloop terminée proprement")
    except Exception as e:
        _log.critical(f"Erreur fatale dans main() : {e}", exc_info=True)
        show_fatal_error(
            f"L'application a planté :\n{e}\n\nVoir le log :\n{log_file}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
