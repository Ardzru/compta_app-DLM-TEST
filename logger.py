import logging
from pathlib import Path

LOG_FILE = Path("traitement.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    encoding="utf-8"   # 🔥 LIGNE CRITIQUE
)

logger = logging.getLogger("compta")
