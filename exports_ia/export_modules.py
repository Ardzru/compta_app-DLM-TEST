# export_modules.py
import os
from pathlib import Path

output = []

# Exporte TOUS les fichiers .py des modules (1, 2, 3)
for module_dir in sorted(Path('modules').iterdir()):
    if module_dir.is_dir() and module_dir.name.startswith('module_'):

        # Fichiers à la racine du module
        for file in sorted(module_dir.glob('*.py')):
            output.append(f"\n{'=' * 60}")
            output.append(f"FICHIER: {file}")
            output.append('=' * 60)
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    output.append(f.read())
            except Exception as e:
                output.append(f"[ERREUR LECTURE: {e}]")

        # Fichiers dans les sous-dossiers (handlers, ui, etc.)
        for subdir in sorted(module_dir.iterdir()):
            if subdir.is_dir() and subdir.name != '__pycache__':
                for file in sorted(subdir.glob('*.py')):
                    output.append(f"\n{'=' * 60}")
                    output.append(f"FICHIER: {file}")
                    output.append('=' * 60)
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            output.append(f.read())
                    except Exception as e:
                        output.append(f"[ERREUR LECTURE: {e}]")

result = '\n'.join(output)

with open('export_modules.txt', 'w', encoding='utf-8') as f:
    f.write(result)

print(f"[OK] Taille: {len(result)} caracteres")
print(f"[OK] Fichier cree: export_modules.txt")
