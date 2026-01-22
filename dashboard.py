import json
from pathlib import Path

LOG_FILE = Path("traitement.log")


def lire_stats():
    stats = {
        "succes": 0,
        "erreurs": 0,
        "avoirs": 0,
        "banque": 0,
        "amex": 0,
        "alma": 0,
        "ancv": 0,
        "kiosk_photo": 0,  # 👈 AJOUT
    }

    if not LOG_FILE.exists():
        return stats

    with LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:

            if "Succès :" in line:
                try:
                    stats["succes"] = int(line.split(":")[-1].strip())
                except:
                    pass

            elif "Erreurs :" in line:
                try:
                    stats["erreurs"] = int(line.split(":")[-1].strip())
                except:
                    pass

            elif "AVOIRS détecté" in line:
                stats["avoirs"] += 1

            elif "BANQUE tentative" in line:
                stats["banque"] += 1

            elif "AMEX CAISSE détecté" in line or "AMEX INTERNET détecté" in line:
                stats["amex"] += 1

            elif "ALMA détecté" in line:
                stats["alma"] += 1

            elif "ANCV détecté" in line:
                stats["ancv"] += 1

            elif "KIOSK PHOTO LUGE détecté" in line:
                stats["kiosk_photo"] += 1

    return stats


def main():
    stats = lire_stats()

    payload = {
        "summary": {
            "total": stats["succes"] + stats["erreurs"],
            "success": stats["succes"],
            "errors": stats["erreurs"],
        },
        "detail": {
            "avoirs": stats["avoirs"],
            "banque": stats["banque"],
            "amex": stats["amex"],
            "alma": stats["alma"],
            "ancv": stats["ancv"],
            "kiosk_photo": stats["kiosk_photo"],  # 👈 AJOUT
        }
    }

    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
