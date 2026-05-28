# export_core.py
import os
from pathlib import Path

output = []

# Exporte TOUS les fichiers .py de core/
for file in sorted(Path('core').glob('*.py')):
    output.append(f"\n{'='*60}")
    output.append(f"FICHIER: {file}")
    output.append('='*60)
    try:
        with open(file, 'r', encoding='utf-8') as f:
            output.append(f.read())
    except Exception as e:
        output.append(f"[ERREUR LECTURE: {e}]")

# Exporte aussi les sous-dossiers (utils, __pycache__, etc.)
for subdir in sorted(Path('core').iterdir()):
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

with open('export_core.txt', 'w', encoding='utf-8') as f:
    f.write(result)

print(f"✓ Taille: {len(result)} caractères")
print(f"✓ Fichier créé: export_core.txt")
