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

def _parser_date_banque(date_c1: str) -> Optional[str]:
    """
    Parse la date bancaire depuis le format court YY/MM/DD
    et retourne la date comptable J-1 au format DD/MM/YYYY.
    Utilisé pour AMEX et PLANET.
    Exemple : '26/01/09' → '25/01/2009'
    """
    try:
        annee_court, mois, jour = date_c1.split("/")
        annee   = f"20{annee_court}"
        jour_j1 = f"{int(jour) - 1:02d}"
        return f"{jour_j1}/{mois}/{annee}"
    except (ValueError, IndexError):
        logger.error(f"Date bancaire invalide : {date_c1!r}")
        return None

def _parser_date_banque_jjmmaa(date_c1: str) -> Optional[str]:
    """
    Parse la date bancaire depuis le format court YY/MM/DD
    et retourne la date au format jjmmaa SANS -1 jour.
    Utilisé pour le libellé CB.
    Exemple : '26/01/09' → '260109'
    """
    try:
        annee_court, mois, jour = date_c1.split("/")
        return f"{jour}{mois}{annee_court}"
    except (ValueError, IndexError):
        logger.error(f"Date bancaire invalide : {date_c1!r}")
        return None

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_banque(fichier: Path) -> Optional[Path]:
    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier BANQUE introuvable : {fichier}")

    logger.info(f"Traitement BANQUE : {fichier.name}")

    lignes_detail = []
    nb_ignores    = 0
    date_ecriture     = None
    date_banque_jjmmaa = None
    piece             = ""

    totaux = {cle: {"ventes": 0, "rembours": 0} for cle in CONTRATS.values()}

    with open(fichier, newline="", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")

        for idx, row in enumerate(reader, start=1):
            if not row:
                continue

            type_ligne = row[0].strip().upper()

            # --------------------------------------------------
            # Ligne TITRE → extraction de la date
            # Format : TITRE ; DOMAINE... ; 26/05/14 02:01:01 ; TABLE_V_CUSTOM
            # --------------------------------------------------
            if type_ligne == "TITRE":
                if len(row) >= 3:
                    date_brut = row[2].strip()  # "20260512 02:01:01"
                    date_part = date_brut.split(" ")[0]  # "20260512"
                    try:
                        # Format YYYYMMDD
                        annee  = date_part[0:4]
                        mois   = date_part[4:6]
                        jour   = int(date_part[6:8])

                        # CB : date J (sans -1)
                        date_banque_jjmmaa = f"{jour:02d}{mois}{annee[2:]}"

                        # AMEX / PLANET : date J-1
                        jour_j1 = f"{jour - 1:02d}"
                        date_ecriture = f"{jour_j1}/{mois}/{annee}"

                    except Exception as e:
                        logger.error(f"Erreur parsing date TITRE : {date_brut!r} → {e}")
                continue

            # --------------------------------------------------
            # Ligne ENTETE → skip
            # --------------------------------------------------
            if type_ligne == "ENTETE":
                continue

            # --------------------------------------------------
            # Ligne TRANSACTION
            # Colonnes : TRANSACTION ; date_paiement ; date_remise ;
            #            commande ; contrat ; type ; montant ; statut
            #            0            1              2
            #            3         4        5      6        7
            # --------------------------------------------------
            if type_ligne == "TRANSACTION":
                if len(row) < 8:
                    nb_ignores += 1
                    continue

                statut      = row[7].strip().upper()
                if statut != "CAPTURED":
                    logger.debug(f"Ligne {idx} ignorée : statut {statut!r}")
                    nb_ignores += 1
                    continue

                commande       = row[3].strip().lstrip("M")
                contrat        = row[4].strip()
                sens_source    = row[5].strip().upper()
                montant_devise = int(row[6].strip())
                montant_eur    = montant_devise / 100

                cle = CONTRATS.get(contrat)
                if not cle:
                    logger.warning(f"Ligne {idx} ignorée : contrat inconnu {contrat!r}")
                    nb_ignores += 1
                    continue

                if sens_source == "DEBIT":
                    d, c = "", format_montant(montant_eur)
                    totaux[cle]["ventes"] += montant_devise

                elif sens_source == "CREDIT":
                    d, c = format_montant(montant_eur), ""
                    totaux[cle]["rembours"] += montant_devise

                else:
                    logger.warning(f"Ligne {idx} ignorée : sens inconnu {sens_source!r}")
                    nb_ignores += 1
                    continue

                lignes_detail.append({
                    "objet": commande,
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
    # Lignes contrepartie bancaire (inchangé)
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
                "d": format_montant(montant_vente),
                "c": "",
            })

        if total_rembours > 0:
            montant_remb = total_rembours / 100
            lignes_via.append({
                "objet": libelle,
                "d": "",
                "c": format_montant(montant_remb),
            })

    # ----------------------------------------------------------
    # Export CSV (inchangé)
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

