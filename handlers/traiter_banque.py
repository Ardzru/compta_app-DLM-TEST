import csv
from pathlib import Path
from config import DOSSIER_SORTIE


# Exception levée si aucune transaction bancaire exploitable n’est trouvée
class NotBanqueFileError(Exception):
    pass


def format_montant(valeur: float) -> str:
    """
    Formate un montant numérique au format comptable français.
    Exemple : 1234.5 → '1234,50'
    """
    return f"{valeur:.2f}".replace(".", ",")


def construire_libelle_total_banque(cle: str, date_ecriture: str) -> str:
    """
    Construit le libellé normalisé pour les lignes de contrepartie banque
    selon le type de contrat.
    """
    if cle == "CB":
        return f"CB DOMAINE DE LOIS DU {date_ecriture}"
    if cle == "AMEX":
        return f"AMEX DU {date_ecriture}"
    if cle == "PLANET":
        return f"PLANET DU {date_ecriture}"
    return f"BANQUE DU {date_ecriture}"


def traiter_banque(fichier: Path):
    """
    Traite un fichier bancaire CSV et génère les écritures comptables.

    MATRICE DE SORTIE :
    STE | DATE | COMPTE | Auxiliaire | n° pièce | OBJET | D | C | Journal | Analytique
    """

    # Constantes comptables
    STE = "DLM"
    COMPTE = "580010DS5"
    AUXILIAIRE = ""
    ANALYTIQUE = ""
    JOURNAL = "CEBOOBA"

    # Détail des transactions (une ligne par commande)
    lignes_detail = []

    # Totaux par type de contrat pour la contrepartie bancaire
    totaux = {
        "AMEX": {"D": 0, "C": 0},
        "PLANET": {"D": 0, "C": 0},
        "CB": {"D": 0, "C": 0},
    }

    # Lecture du fichier CSV bancaire
    with open(fichier, newline="", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")

        # 🔹 Lecture de la première ligne (C1)
        # Exemple : 26/01/09_03:01:28
        premiere_ligne = next(reader)
        date_c1 = premiere_ligne[2].split("_")[0]  # 26/01/09

        # Décomposition de la date bancaire
        annee_banque, mois, jour_banque = date_c1.split("/")

        # Reconstitution de la date comptable
        annee = f"20{annee_banque}"
        jour = f"{int(jour_banque) - 1:02d}"  # J-1

        date_ecriture = f"{jour}/{mois}/{annee}"
        piece = f"JOURNEE DU {date_ecriture}"

        # Parcours des transactions
        for row in reader:
            # Ligne invalide ou incomplète
            if not row or len(row) < 9:
                continue

            # On ne garde que les lignes TRANSACTION
            if row[0].strip().upper() != "TRANSACTION":
                continue

            # On ne garde que les transactions CAPTURED
            if row[7].strip().upper() != "CAPTURED":
                continue

            # Extraction des données utiles
            commande = row[3].strip().lstrip("M")
            contrat = row[4].strip()
            sens_source = row[5].strip().upper()
            montant_devise = int(row[6].strip())
            montant_eur = montant_devise / 100

            # Sens comptable
            if sens_source == "DEBIT":
                d = ""
                c = format_montant(montant_eur)
                sens_compte = "C"
            elif sens_source == "CREDIT":
                d = format_montant(montant_eur)
                c = ""
                sens_compte = "D"
            else:
                continue

            # Identification du type de contrat
            if contrat == "7770571305":
                cle = "AMEX"
            elif contrat == "831103222":
                cle = "PLANET"
            elif contrat == "8430996":
                cle = "CB"
            else:
                continue

            # 🔹 Ligne de détail par commande
            lignes_detail.append({
                "objet": commande,
                "d": d,
                "c": c
            })

            # Cumul des totaux pour la contrepartie
            totaux[cle][sens_compte] += montant_devise

    # Aucun mouvement bancaire détecté
    if not lignes_detail:
        raise NotBanqueFileError("Aucune ligne BANQUE CAPTURED détectée")

    # 🔹 Construction des lignes de contrepartie (VIA banque)
    lignes_via = []

    for cle, valeurs in totaux.items():
        total_c = valeurs["C"]
        total_d = valeurs["D"]

        # Équilibré → rien à générer
        if total_c == total_d:
            continue

        montant = abs(total_c - total_d) / 100

        if total_c > total_d:
            d = format_montant(montant)
            c = ""
        else:
            d = ""
            c = format_montant(montant)

        lignes_via.append({
            "objet": construire_libelle_total_banque(cle, date_ecriture),
            "d": d,
            "c": c
        })

    # 🔹 Export du fichier comptable CSV
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_banque.csv"

    with open(sortie, "w", newline="", encoding="latin1") as f:
        writer = csv.writer(f, delimiter=";")

        # En-tête comptable
        writer.writerow([
            "STE", "DATE", "COMPTE", "Auxiliaire",
            "n° pièce", "OBJET", "D", "C",
            "Journal", "Analytique"
        ])

        # Lignes de détail (par commande)
        for l in lignes_detail:
            writer.writerow([
                STE, date_ecriture, COMPTE, AUXILIAIRE,
                piece, l["objet"], l["d"], l["c"],
                JOURNAL, ANALYTIQUE
            ])

        # Lignes de contrepartie bancaire
        for l in lignes_via:
            writer.writerow([
                STE, date_ecriture, COMPTE, AUXILIAIRE,
                piece, l["objet"], l["d"], l["c"],
                JOURNAL, ANALYTIQUE
            ])

    return sortie
