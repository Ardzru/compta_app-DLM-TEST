📊 Import Comptabilité – Automatisation des flux
🎯 Objectif
Cette application permet de traiter automatiquement les fichiers comptables issus de différentes sources (banque, prestataires de paiement, billetterie, kiosque photo, etc.) et de générer des fichiers CSV prêts à être importés en comptabilité.

Elle est conçue pour être :

fiable

lisible

maintenable

exploitable sur serveur avec accès limité

📁 Principe général
Les fichiers sources sont déposés dans le dossier fichiers_brut

Le traitement est lancé via l’interface web ou en ligne de commande

Chaque fichier est :

détecté

traité par le handler correspondant

transformé en écritures comptables

Les fichiers traités sont archivés par date

Les résultats sont visibles dans le dashboard

📂 Arborescence simplifiée
Code
compta_app/
│
├── fichiers_brut/        # Fichiers à traiter
├── archive/              # Archivage par date
├── sortie/               # Fichiers CSV comptables générés
│
├── core/
│   ├── dispatcher.py     # Détection et routage des fichiers
│   └── handlers/
│       ├── traiter_alma.py
│       ├── traiter_banque.py
│       ├── traiter_ta.py
│       ├── traiter_ancv.py
│       ├── traiter_avoirs.py
│       ├── traiter_kiosk_photo.py
│       ├── traiter_amex_internet.py
│       └── traiter_amex_caisse.py
│
├── dashboard.py          # API statistiques
├── templates/
│   └── dashboard.html    # Interface web
│
├── config.py             # Paramètres globaux
├── logger.py             # Journalisation
└── README.md
🔄 Flux pris en charge
🟦 ALMA
Lecture Excel

Gestion des montants, TVA et frais

Écritures :

Compte ALMA

TVA collectée

Frais

Encaissement net

🟩 BANQUE
Lecture CSV bancaire

Filtrage des transactions CAPTURED

Gestion des contrats :

CB

AMEX

PLANET

Écritures détaillées par commande

Contreparties regroupées par type

🟨 TA (Billetterie / Caisse)
Lecture Excel

Gestion des ventes et annulations

Regroupement :

par numéro de commande

par caisse

Écritures équilibrées par journée

🟧 ANCV Connect
Lecture CSV

Filtrage métier :

VALIDATED

Transaction finalisée

Montant positif

Distinction :

Internet (référence 8 caractères)

Caisse

Contreparties regroupées par date et type

🟥 AVOIRS
Lecture Excel

Gestion des statuts FR / EN

Détermination automatique du sens comptable

Deux écritures par ligne :

Compte commande

Compte avoir

Libellés explicites (nom, prénom, expiration)

📸 KIOSK PHOTO LUGE
Lecture CSV ou Excel

Exclusion des ventes par jetons

Répartition automatique :

Monnayeur → compte 580001

TPE → compte 580005

Calcul automatique :

CA HT

TVA collectée

Écritures journalières équilibrées

💳 AMEX INTERNET
Lecture Excel (.xls / .xlsx)

Filtrage des lignes SITE

Gestion des cas :

Remboursement

Encaissement simple

Encaissement avec frais

Comptes et journaux adaptés

💳 AMEX CAISSE
Lecture Excel (.xls / .xlsx)

Filtrage signature DLM

Gestion des mêmes cas que AMEX Internet

Comptes spécifiques caisse

Journal dédié

📊 Dashboard
Le dashboard affiche :

Nombre total de fichiers traités

Nombre d’erreurs

Détail par flux :

ALMA

BANQUE

TA

ANCV

AVOIRS

AMEX

KIOSK PHOTO LUGE

Les statistiques sont basées sur les logs, garantissant une source fiable.

🧾 Archivage
Tous les fichiers traités sont déplacés dans :

Code
archive/YYYY-MM-DD/
Les fichiers temporaires (ex : conversions .xls → .xlsx) sont nettoyés

Aucun fichier traité ne reste dans fichiers_brut

🔐 Sécurité & robustesse
Verrou système empêchant les doubles exécutions

Gestion des erreurs par flux

Logs explicites et auditables

Code commenté métier, pas technique

🏁 État du projet
✔️ Tous les flux intégrés

✔️ Code commenté et lisible

✔️ Documentation alignée

✔️ Prêt pour serveur

✔️ Version figée (V1)

✍️ Auteur
Application conçue et développée par Matthias Carvalho  
Automatisation comptable – Domaine de Loisirs de Morzine