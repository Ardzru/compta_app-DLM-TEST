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

def _parser_date_banque(date_str: str) -> Optional[str]:
    """
    Parse 'aa/mm/jj_hh:mm:ss' → date J-1 au format jj/mm/aaaa
    Ex : '26/05/14_02:01:01' → '13/05/2026'
    """
    try:
        date_part = date_str.split("_")[0]        # '26/05/14'
        aa, mm, jj = date_part.split("/")
        jour_j1 = f"{int(jj) - 1:02d}"
        return f"{jour_j1}/{mm}/20{aa}"
    except (ValueError, IndexError):
        logger.error(f"Date bancaire invalide : {date_str!r}")
        return None

def _parser_date_banque_jjmmaa(date_str: str) -> Optional[str]:
    """
    Parse 'aa/mm/jj_hh:mm:ss' → jjmmaa SANS -1
    Ex : '26/05/14_02:01:01' → '140526'
    """
    try:
        date_part = date_str.split("_")[0]        # '26/05/14'
        aa, mm, jj = date_part.split("/")
        return f"{jj}{mm}{aa}"
    except (ValueError, IndexError):
        logger.error(f"Date bancaire invalide : {date_str!r}")
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
    totaux = {cle: {"ventes": 0, "rembours": 0} for cle in CONTRATS.values()}

    with open(fichier, newline="", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")

        # ----------------------------------------------------------
        # 1. Chercher la ligne TITRE pour extraire la date
        # ----------------------------------------------------------
        date_ecriture      = None
        date_banque_jjmmaa = None
        piece              = ""

        for row in reader:
            if not row:
                continue
            if row[0].strip().upper() == "TITRE":
                # TITRE;NOM;aa/mm/jj_hh:mm:ss;...
                if len(row) < 3:
                    raise NotBanqueFileError(f"Ligne TITRE incomplète : {fichier.name}")
                date_raw           = row[2].strip()
                date_ecriture      = _parser_date_banque(date_raw)
                date_banque_jjmmaa = _parser_date_banque_jjmmaa(date_raw)
                piece              = row[1].strip() if len(row) > 1 else ""
                break
        else:
            raise NotBanqueFileError(f"Ligne TITRE introuvable : {fichier.name}")

        if not date_ecriture:
            raise NotBanqueFileError(f"Date invalide dans TITRE : {fichier.name}")

        # ----------------------------------------------------------
        # 2. Lecture des lignes TRANSACTION
        # ----------------------------------------------------------
        for idx, row in enumerate(reader, start=2):
            if len(row) < 8:
                nb_ignores += 1
                continue

            type_ligne = row[0].strip().upper()
            statut     = row[7].strip().upper()

            if type_ligne != "TRANSACTION":
                nb_ignores += 1
                continue

            if statut != "CAPTURED":
                logger.debug(f"Ligne {idx} ignorée : statut {statut!r}")
                nb_ignores += 1
                continue

            commande    = row[3].strip().lstrip("M")
            contrat     = row[4].strip()
            sens_source = row[5].strip().upper()
            try:
                montant_devise = int(row[6].strip())
            except ValueError:
                nb_ignores += 1
                continue

            montant_eur = montant_devise / 100

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

            lignes_detail.append({"objet": commande, "d": d, "c": c})

    # ----------------------------------------------------------
    # 3. Vérification
    # ----------------------------------------------------------
    if not lignes_detail:
        raise NotBanqueFileError(f"Aucune transaction CAPTURED trouvée dans {fichier.name}")

    logger.info(f"{len(lignes_detail)} transactions traitées ({nb_ignores} lignes ignorées)")

    # ----------------------------------------------------------
    # 4. Lignes de contrepartie bancaire
    # ----------------------------------------------------------
    lignes_via = []

    for cle, valeurs in totaux.items():
        total_ventes   = valeurs["ventes"]
        total_rembours = valeurs["rembours"]
        libelle = _construire_libelle_banque(cle, date_ecriture, date_banque_jjmmaa)

        if total_ventes > 0:
            montant_vente = total_ventes / 100
            lignes_via.append({"objet": libelle, "d": format_montant(montant_vente), "c": ""})
            logger.debug(f"Contrepartie VENTE {cle} : {format_montant(montant_vente)} D")

        if total_rembours > 0:
            montant_remb = total_rembours / 100
            lignes_via.append({"objet": libelle, "d": "", "c": format_montant(montant_remb)})
            logger.debug(f"Contrepartie REMBOURSEMENT {cle} : {format_montant(montant_remb)} C")

    # ----------------------------------------------------------
    # 5. Export CSV
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

    logger.info(f"Export BANQUE : {sortie.name} ({len(lignes_detail + lignes_via)} écritures)")
    return sortie
