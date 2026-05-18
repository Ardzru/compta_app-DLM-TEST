import csv
from pathlib import Path
from typing import Optional
from config import DOSSIER_SORTIE
from logger import logger

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotBanqueFileError(Exception):
    """Levée si aucune transaction bancaire exploitable n'est trouvée."""
    pass

# ==========================================================
# CONSTANTES COMPTABLES
# ==========================================================
STE        = "DLM"
COMPTE     = "580010DS5"
JOURNAL    = "CEBOOBA"
AUXILIAIRE = ""
ANALYTIQUE = ""

# ==========================================================
# MAPPING CONTRATS → CLÉ MÉTIER
# ==========================================================
CONTRATS = {
    "7770571305": "AMEX",
    "831103222":  "PLANET",
    "8430996":    "CB",
}

# ==========================================================
# UTILITAIRES
# ==========================================================

def format_montant(valeur: float) -> str:
    """Formate un montant en chaîne comptable française. Ex : 1234.5 → '1234,50'"""
    return f"{abs(valeur):.2f}".replace(".", ",")

def _construire_libelle_banque(cle: str, date_ecriture: str, date_banque_jjmmaa: str) -> str:
    """Construit le libellé normalisé pour les lignes de contrepartie banque."""
    if cle == "CB":
        return f"CB DOMAINE DE LOIS {date_banque_jjmmaa}"
    elif cle == "AMEX":
        return f"AMEX DU {date_ecriture}"
    elif cle == "PLANET":
        return f"PLANET DU {date_ecriture}"
    else:
        return f"{cle} DU {date_ecriture}"

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_banque(fichier: Path) -> Optional[Path]:
    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier BANQUE introuvable : {fichier}")

    logger.info(f"Traitement BANQUE : {fichier.name}")

    lignes_detail      = []
    nb_ignores         = 0
    date_ecriture      = None
    date_banque_jjmmaa = None
    piece              = ""

    totaux = {cle: {"ventes": 0, "rembours": 0} for cle in CONTRATS.values()}

    with open(fichier, newline="", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")

        for idx, row in enumerate(reader):
            if not row:
                continue

            type_ligne = row[0].strip().upper()

            # --------------------------------------------------
            # 1. TITRE → extraction date
            # --------------------------------------------------
            if type_ligne == "TITRE":
                if len(row) >= 3:
                    date_brut = row[2].strip()           # "26/05/14_02:01:01"
                    date_part = date_brut.split("_")[0]  # "26/05/14"
                    try:
                        aa, mm, jj = date_part.split("/")  # "26", "05", "14"
                        annee = f"20{aa}"                  # "2026"

                        date_ecriture      = f"{jj}/{mm}/{annee}"  # "14/05/2026"
                        date_banque_jjmmaa = f"{jj}{mm}{aa}"       # "140526"

                        logger.debug(
                            f"Date écriture : {date_ecriture} | "
                            f"Date banque jjmmaa : {date_banque_jjmmaa}"
                        )
                    except Exception as e:
                        logger.error(f"Erreur parsing date TITRE : {date_brut!r} → {e}")
                continue

            # --------------------------------------------------
            # 2. CONTRAT → extraction numéro de pièce
            # --------------------------------------------------
            if type_ligne == "CONTRAT":
                if len(row) >= 2:
                    piece = row[1].strip()
                    logger.debug(f"Numéro de pièce : {piece}")
                continue

            # --------------------------------------------------
            # 3. DETAIL → transactions CAPTURED
            # --------------------------------------------------
            if type_ligne == "DETAIL":
                if len(row) < 6:
                    nb_ignores += 1
                    continue

                statut    = row[3].strip().upper()
                contrat   = row[1].strip()
                type_op   = row[4].strip().upper()

                if statut != "CAPTURED":
                    nb_ignores += 1
                    continue

                cle = CONTRATS.get(contrat)
                if not cle:
                    logger.warning(f"Contrat inconnu ligne {idx+1} : {contrat!r}")
                    nb_ignores += 1
                    continue

                try:
                    montant_brut = int(row[5].strip())
                except ValueError:
                    logger.error(f"Montant invalide ligne {idx+1} : {row[5]!r}")
                    nb_ignores += 1
                    continue

                montant_float = montant_brut / 100

                if type_op == "VENTE":
                    totaux[cle]["ventes"] += montant_brut
                    objet = f"VTE {cle} {date_banque_jjmmaa}"
                    d, c  = format_montant(montant_float), ""

                elif type_op == "REMBOURSEMENT":
                    totaux[cle]["rembours"] += montant_brut
                    objet = f"RBT {cle} {date_banque_jjmmaa}"
                    d, c  = "", format_montant(montant_float)

                else:
                    logger.warning(f"Type opération inconnu ligne {idx+1} : {type_op!r}")
                    nb_ignores += 1
                    continue

                lignes_detail.append({
                    "objet": objet,
                    "d":     d,
                    "c":     c,
                })

            else:
                nb_ignores += 1

    # ----------------------------------------------------------
    # Vérifications
    # ----------------------------------------------------------
    if not date_ecriture:
        raise NotBanqueFileError(
            f"Aucune ligne TITRE avec date valide dans {fichier.name}"
        )

    if not lignes_detail:
        raise NotBanqueFileError(
            f"Aucune transaction CAPTURED trouvée dans {fichier.name}"
        )

    logger.info(
        f"{len(lignes_detail)} transactions traitées "
        f"({nb_ignores} lignes ignorées)"
    )

    # ----------------------------------------------------------
    # Lignes contrepartie bancaire
    # ----------------------------------------------------------
    lignes_via = []

    for cle, valeurs in totaux.items():
        total_ventes   = valeurs["ventes"]
        total_rembours = valeurs["rembours"]

        libelle = _construire_libelle_banque(cle, date_ecriture, date_banque_jjmmaa)

        if total_ventes > 0:
            montant_vente = total_ventes / 100
            lignes_via.append({
                "objet": libelle,
                "d":     format_montant(montant_vente),
                "c":     "",
            })

        if total_rembours > 0:
            montant_remb = total_rembours / 100
            lignes_via.append({
                "objet": libelle,
                "d":     "",
                "c":     format_montant(montant_remb),
            })

    # ----------------------------------------------------------
    # Export CSV
    # ----------------------------------------------------------
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    sortie = DOSSIER_SORTIE / f"{fichier.stem}_banque.csv"

    with open(sortie, "w", newline="", encoding="latin1") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "STE", "DATE", "COMPTE", "Auxiliaire",
            "n°pièce", "OBJET", "D", "C",
            "Journal", "Analytique",
        ])

        for l in lignes_detail + lignes_via:
            writer.writerow([
                STE, date_ecriture, COMPTE, AUXILIAIRE,
                piece, l["objet"], l["d"], l["c"],
                JOURNAL, ANALYTIQUE,
            ])

    logger.info(
        f"Export BANQUE : {sortie.name} "
        f"({len(lignes_detail + lignes_via)} écritures)"
    )
    return sortie
