# export_racine.py
import os

files = ['app.py', 'config.py', 'logger.py', 'dashboard.py']
output = []

for file in files:
    if os.path.exists(file):
        output.append(f"\n{'='*60}")
        output.append(f"FICHIER: {file}")
        output.append('='*60)
        with open(file, 'r', encoding='utf-8') as f:
            output.append(f.read())

with open('export_racine.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Taille:", len('\n'.join(output)), "caractères")
