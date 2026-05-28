# fix_handlers.py - CORRIGÉ
from pathlib import Path

HANDLERS_DIR = Path("modules/module_1/handlers")

# Liste RÉELLE des fichiers (d'après ta capture)
HANDLERS = {
    "traiter_alma": "amex_alma",
    "traiter_amex_caisse": "amex_caisse",
    "traiter_amex_internet": "amex_internet",
    "traiter_ancv": "ancv",
    "traiter_avoirs": "avoirs",
    "traiter_banque": "banque",
    "traiter_kiosk_photo": "kiosk_photo",
    "traiter_planet": "planet",
    "traiter_ta": "ta",
}

for handler_name, type_key in HANDLERS.items():
    filepath = HANDLERS_DIR / f"{handler_name}.py"

    if not filepath.exists():
        print(f"⚠️  {handler_name}.py : pas trouvé")
        continue

    content = filepath.read_text(encoding="utf-8")

    # Nom de la classe CORRECT (ex: traiter_alma → TraiterAlmaHandler, PAS TraiterTraiterAlmaHandler)
    words = handler_name.replace("traiter_", "").split("_")
    class_name = "Traiter" + "".join(w.capitalize() for w in words) + "Handler"
    func_name = handler_name

    # Ajouter la classe si elle n'existe pas
    if f"class {class_name}" not in content:
        class_code = f'''

# ==========================================================
# CLASSE HANDLER
# ==========================================================

class {class_name}:
    """Handler pour traiter les fichiers {type_key}."""

    @staticmethod
    def traiter(fichier: Path) -> None:
        """Traite un fichier {type_key}."""
        {func_name}(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """Vérifie si c'est un fichier {type_key}."""
        return detecteur_result.get("type") == "{type_key}"


__all__ = ['{class_name}', '{func_name}']
'''
        content += class_code
        filepath.write_text(content, encoding="utf-8")
        print(f"✅ {handler_name}.py : classe {class_name} AJOUTÉE")
    else:
        print(f"⏭️  {handler_name}.py : classe {class_name} existe déjà")

print("\n✅ FIX TERMINÉ !")
