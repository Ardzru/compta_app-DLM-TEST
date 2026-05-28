import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent  # racine du projet
PROJECT_ROOT = SCRIPT_DIR

output = []

# Exporte TOUS les fichiers .py de core/
for file in sorted((PROJECT_ROOT / 'core').glob('*.py')):
    output.append(f"\n{'='*60}")
    output.append(f"FICHIER: {file}")
    output.append('='*60)
    try:
        with open(file, 'r', encoding='utf-8') as f:
            output.append(f.read())
    except Exception as e:
        output.append(f"[ERREUR LECTURE: {e}]")

# Exporte aussi les sous-dossiers
for subdir in sorted((PROJECT_ROOT / 'core').iterdir()):
    if subdir.is_dir() and subdir.name != '__pycache__':
        for file in sorted(subdir.glob('*.py')):
            output.append(f"\n{'='*60}")
            output.append(f"FICHIER: {file}")
            output.append('='*60)
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    output.append(f.read())
            except Exception as e:
                output.append(f"[ERREUR LECTURE: {e}]")

result = '\n'.join(output)

with open(PROJECT_ROOT / 'export_core.txt', 'w', encoding='utf-8') as f:
    f.write(result)

print(f"✓ Taille: {len(result)} caractères")
print(f"✓ Fichier créé: export_core.txt")
