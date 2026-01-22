📘 Guide Utilisateur
Application d’import comptable automatisé
🎯 À quoi sert cette application ?
Cette application permet de transformer automatiquement des fichiers de ventes et de paiements en fichiers comptables prêts à être importés dans le logiciel de comptabilité.

Elle évite :

les saisies manuelles

les erreurs humaines

les oublis de fichiers

les calculs manuels de TVA ou de frais

🧑‍💼 À qui s’adresse ce guide ?
Ce guide est destiné à :

toute personne déposant les fichiers

toute personne lançant le traitement

toute personne consultant les résultats

👉 Aucune connaissance technique n’est nécessaire.

📂 Où déposer les fichiers ?
Tous les fichiers à traiter doivent être déposés dans le dossier :

Code
fichiers_brut/
⚠️ Important

Ne pas renommer les fichiers

Ne pas modifier leur contenu

Déposer uniquement des fichiers à traiter

📄 Types de fichiers acceptés
Type	Origine
ALMA	Paiement en plusieurs fois
BANQUE	Relevés bancaires
TA	Billetterie / caisse
ANCV	Chèques vacances
AVOIRS	Avoirs clients
AMEX Internet	Paiements AMEX en ligne
AMEX Caisse	Paiements AMEX en caisse
KIOSK PHOTO LUGE	Ventes kiosque photo
▶️ Comment lancer le traitement ?
Méthode 1 — Interface web (recommandée)
Ouvrir l’application dans le navigateur

Cliquer sur « Lancer le traitement »

Attendre la confirmation de fin

Méthode 2 — Ligne de commande (si nécessaire)
bash
python traiter_dossier.py
⏳ Pendant le traitement
Les fichiers sont analysés un par un

Chaque fichier est automatiquement reconnu

Les écritures comptables sont générées

Les erreurs éventuelles sont enregistrées

⚠️ Ne pas fermer l’application pendant le traitement

📁 Où sont les résultats ?
📤 Fichiers comptables générés
Les fichiers comptables sont créés dans le dossier :

Code
sortie/
Ils sont au format CSV, prêts à être importés en comptabilité.

📦 Archivage automatique
Les fichiers traités sont déplacés dans :

Code
archive/YYYY-MM-DD/
👉 Le dossier fichiers_brut est vidé automatiquement.

📊 Consulter le tableau de bord
Le tableau de bord affiche :

nombre de fichiers traités

nombre d’erreurs

détail par type de flux

Il permet de vérifier rapidement que tout s’est bien passé.

❌ Que faire en cas d’erreur ?
Cas 1 — Aucun fichier traité
Vérifier que les fichiers sont bien dans fichiers_brut

Vérifier que le format est correct

Cas 2 — Erreur sur un fichier
Le fichier reste archivé

L’erreur est visible dans les logs

Le reste du traitement continue normalement

👉 Un fichier en erreur n’empêche pas les autres d’être traités.

🔐 Sécurité intégrée
Impossible de lancer deux traitements en même temps

Les fichiers ne sont jamais écrasés

Les montants sont recalculés automatiquement

Les règles comptables sont figées

🧾 Bonnes pratiques
✔️ Déposer les fichiers une seule fois
✔️ Vérifier le dashboard après traitement
✔️ Importer les fichiers CSV générés sans modification
✔️ Ne jamais modifier les fichiers archivés

🏁 En résumé
Déposer les fichiers dans fichiers_brut

Lancer le traitement

Récupérer les fichiers dans sortie

Importer en comptabilité

Vérifier le dashboard

✍️ Auteur
Application développée par Matthias Carvalho  
Automatisation comptable – Domaine de Loisirs de Morzine