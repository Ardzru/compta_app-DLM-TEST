# Module 2 — Justification Compte Internet

## 🎯 Objectif
Rapprocher les écritures comptables (COMPTA) avec les remises bancaires (BANQUE) 
et les commandes Alpilink (ALPILINK) pour justifier les paiements.

## 📊 Flux

Fichiers bruts (COMPTA + BANQUE + ALPILINK)
        ↓
  [CHARGEMENT] → Lecture fichiers Excel/CSV
        ↓
  [EXTRACTION] → Normalisation commandes (8 chiffres)
        ↓
 [RAPPROCHEMENT] → Croisement par numéro de commande
        ↓
   [EXPORT EXCEL] → Rapport avec couleurs


## 🏗️ Architecture

### Handlers (métier)
- **`compta_handler.py`** — Lecture écritures comptables
  - Valide : journal + montant + date
  - Rejette : libellés non-reconnus (PRO partenaires)
  
- **`banque_handler.py`** — Lecture remises bancaires
  - Détecte colonnes (date, commande, montant)
  - Normalise montants français (1.234,56)
  
- **`alpilink_handler.py`** — Lecture données Alpilink
  - Sépare NORMAL / BUYCLUB
  - Valide canal de vente

### Orchestrateur
- **`justification_handler.py`** — JustificationHandler
  - Lance 4 phases en parallèle (thread)
  - Gère callbacks (log, progression, résultats)
  - Exporte Excel avec couleurs

### UI
- **`justification_view.py`** — Interface Tkinter
  - Détection automatique fichiers
  - Tableau résultats
  - Export manuel Excel

## 🔧 Utilisation

### Depuis l'interface

    Placer fichiers dans dossier brut
    Cliquer "🔄 Rafraîchir"
    Cliquer "▶ Lancer la justification"
    Consulter tableau (validées / non-justifiées / erreurs)
    Cliquer "📥 Exporter Excel" (optionnel)


### Depuis le code
```python
from modules.module_2.justification_handler import JustificationHandler

handler = JustificationHandler(
    callback_log=print,
    callback_fin=afficher_resultats,
    callback_progression=maj_barre
)
handler.lancer(fichiers, dossier_sortie)

📋 Format fichiers
COMPTA (obligatoire)

Colonnes requises :

    Montant Signé (float)
    Journal (string, ex: "VE")
    Sens (string, "D" ou "C")
    Num Commande (8 chiffres)
    Date (DD/MM/YYYY)

Libellés acceptés :

    PRO partenaires (commandes valides)
    Autres → rejetés avec raison

BANQUE (optionnel mais recommandé)

Colonnes detéctées automatiquement :

    Date du paiement
    Numéro de commande
    Montant du paiement
    Contrat (pour la traçabilité)

Format : Excel XLSX ou CSV (; séparateur)
ALPILINK (optionnel)

Colonnes attendues :

    ID Commande (8 chiffres)
    Canal de vente (NORMAL ou BUYCLUB)
    Statut (ex: "Payée banque")
    Prix total (float)

🎨 Résultats (Export Excel)
Onglet "Validées" (VERT ✅)

Commande | Montant Compta | Montant Banque | Écart | Statut           | Source
12345678 | 100.50        | 100.50        | 0.00  | justifiée (all)  | banque + alpilink

Coloration :

    VERT = Écarts nuls
    JAUNE = Écarts détectés (< 5%)

Onglet "Non justifiées" (ROUGE ❌)

Commande | Montant Compta | Statut           | Raison
12345679 | 50.25         | non justifiée    | pas de banque/alpilink

Onglet "Libellés inconnus" (ORANGE ⚠️)

Libellé          | Montant | Fichier      | Raison
"Fournitures"    | 25.00   | compta.xlsx  | non reconnu (PRO requis)

Onglet "Erreurs format" (ORANGE ⚠️)

Fichier      | Erreur
banque2.csv  | Format invalide (colonnes manquantes)

🔍 Rapprochement (logique)

# Pour chaque commande COMPTA
if (commande en BANQUE) AND (commande en ALPILINK):
    → "justifiée (banque + alpilink)"  ✅ VERT
    → Vérifier écarts montants
    
elif (commande en BANQUE):
    → "justifiée (banque)"  ✅ VERT
    
elif (commande en ALPILINK):
    → "justifiée (alpilink)"  ✅ VERT
    
else:
    → "non justifiée"  ❌ ROUGE

📊 Métriques de sortie

{
    "validees": 245,        # Commandes rapprochées
    "non_valides": 12,      # Commandes seules en compta
    "erreurs_fmt": 3,       # Libellés non-reconnus
    "ecart_moyen": 0.45,    # Différence moyenne (%)
}

⚙️ Configuration

Variables d'environnement / config.py :

DOSSIER_BRUT = Path("/share-01/dlm/fichiers_brut")
DOSSIER_SORTIE = Path("/share-01/dlm/sorties/justification")

🐛 Troubleshooting
"Type de fichier inconnu"

→ Vérifier colonnes du fichier
→ S'assurer qu'il est XLSX ou CSV
"Aucune commande exploitable"

→ Vérifier format numéro commande (doit être 8 chiffres)
→ Vérifier montant ≠ 0
"Montants ne correspondent pas"

→ Vérifier séparateur décimal (, ou .)
→ Vérifier absence de symboles monétaires
Écarts importants

→ Vérifier les frais bancaires / TVA non inclus
→ Consulter le détail ligne par ligne (Excel)
📚 Développement
Ajouter un nouveau handler

    Créer modules/module_2/handlers/nouveau_handler.py
    Implémenter charger_XXX() et extraire_commandes()
    Retourner (list[dict], list[dict])
    Importer dans justification_handler.py
    Ajouter détection dans _detecter_type()

Tests

# Valider rapprochement complet
python -m pytest modules/module_2/tests/ -v
