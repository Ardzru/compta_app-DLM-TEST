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
JOURNAL    = "CEBOOBA"
AUXILIAIRE = ""
ANALYTIQUE = ""

COMPTE_DEFAULT = "580010DS5"

# ==========================================================
# MAPPING CONTRATS → CLÉ MÉTIER
# ==========================================================
CONTRATS = {
    "7770571305": "AMEX",
    "831103222":  "PLANET",
    "8430996":    "CB",
}

# ==========================================================
# CONFIG PAR TYPE DE CONTRAT
# ==========================================================
CONFIG_CONTRAT = {
    "CB": {
        "compte":  "580010DS5",
        "journal": "CEBOOBA",
    },
    "AMEX": {
        "compte":  "580010DS5",
        "journal": "CEBOOBA",
    },
    "PLANET": {
        "compte":  "580010DS5",
        "journal": "CEBOOBA",
    },
}

# ==========================================================
# UTILITAIRES
# ==========================================================

def format_montant(valeur: float) -> str:
    return f"{abs(valeur):.2f}".replace(".", ",")

def _construire_libelle_banque(cle: str, date_ecriture: str, date_banque_jjmmaa: str) -> str:
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

    with open(fichier, newline="", encoding="utf-8-sig") as f:
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
                    date_brut = row[2].strip()
                    date_part = date_brut.split("_")[0]
                    try:
                        jj, mm, aa = date_part.split("/")
                        annee = f"20{aa}"

                        date_ecriture      = f"{jj}/{mm}/{annee}"
                        date_banque_jjmmaa = f"{jj}{mm}{aa}"

                        logger.debug(
                            f"Date écriture : {date_ecriture} | "
                            f"Date banque jjmmaa : {date_banque_jjmmaa}"
                        )
                    except Exception as e:
                        logger.error(f"Erreur parsing date TITRE : {date_brut!r} → {e}")
                continue

            # --------------------------------------------------
            # 2. ENTETE → ignoré
            # --------------------------------------------------
            if type_ligne == "ENTETE":
                continue

            # --------------------------------------------------
            # 3. TRANSACTION → traitement
            # --------------------------------------------------
            if type_ligne == "TRANSACTION":
                if len(row) < 8:
                    logger.warning(f"Ligne {idx+1} trop courte : {row}")
                    nb_ignores += 1
                    continue

                statut  = row[7].strip().upper()
                if statut != "CAPTURED":
                    nb_ignores += 1
                    continue

                contrat = row[4].strip()
                type_op = row[5].strip().upper()

                if not contrat:
                    nb_ignores += 1
                    continue

                cle = CONTRATS.get(contrat)
                if not cle:
                    logger.warning(f"Contrat inconnu ligne {idx+1} : {contrat!r}")
                    nb_ignores += 1
                    continue

                try:
                    montant_brut = int(row[6].strip())
                except ValueError:
                    logger.error(f"Montant invalide ligne {idx+1} : {row[6]!r}")
                    nb_ignores += 1
                    continue

                montant_float = montant_brut / 100

                if type_op == "DEBIT":
                    totaux[cle]["ventes"] += montant_brut
                    objet = f"VTE {cle} {date_banque_jjmmaa}"
                    d, c  = format_montant(montant_float), ""

                elif type_op == "CREDIT":
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
                    "cle":   cle,
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
    # Lignes contrepartie banque (une par contrat actif)
    # ----------------------------------------------------------
    lignes_via = []
    for cle in CONTRATS.values():
        total_ventes   = totaux[cle]["ventes"]
        total_rembours = totaux[cle]["rembours"]
        libelle = _construire_libelle_banque(cle, date_ecriture, date_banque_jjmmaa)

        if total_ventes > 0:
            lignes_via.append({
                "objet": libelle,
                "d":     format_montant(total_ventes / 100),
                "c":     "",
                "cle":   cle,
            })

        if total_rembours > 0:
            lignes_via.append({
                "objet": libelle,
                "d":     "",
                "c":     format_montant(total_rembours / 100),
                "cle":   cle,
            })

    toutes_lignes = lignes_detail + lignes_via

    # ----------------------------------------------------------
    # Export : un seul fichier CSV
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

        for l in toutes_lignes:
            cfg     = CONFIG_CONTRAT.get(l["cle"], {})
            compte  = cfg.get("compte",  COMPTE_DEFAULT)
            journal = cfg.get("journal", JOURNAL)

            writer.writerow([
                STE, date_ecriture, compte, AUXILIAIRE,
                piece, l["objet"], l["d"], l["c"],
                journal, ANALYTIQUE,
            ])

    logger.info(f"Export BANQUE : {sortie.name} ({len(toutes_lignes)} écritures)")
    return sortie
