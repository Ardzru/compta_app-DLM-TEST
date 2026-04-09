import logging
from pathlib import Path

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "traitement.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    encoding="utf-8"   # 🔥 LIGNE CRITIQUE
)

logger = logging.getLogger("compta")
