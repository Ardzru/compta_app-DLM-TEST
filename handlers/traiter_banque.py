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
    else:
        return f"{cle} DU {date_ecriture}"

def _parser_date_banque(date_c1: str) -> Optional[str]:
    """
    Parse la date bancaire depuis le format court YY/MM/DD
    et retourne la date comptable J-1 au format DD/MM/YYYY.
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
    et retourne la date au format jjmmaa.
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
    """
    Traite un fichier bancaire CSV et génère les écritures comptables.

    Structure de sortie :
    STE | DATE | COMPTE | Auxiliaire | n°pièce | OBJET | D | C | Journal | Analytique

    Règles métier :
    - Seules les lignes TRANSACTION + CAPTURED sont traitées
    - Contrats reconnus : AMEX / PLANET / CB
    - DEBIT  source = vente        → C (crédit comptable)
    - CREDIT source = remboursement → D (débit  comptable)
    - Contrepartie banque : VENTE → D, REMBOURSEMENT → C (2 lignes séparées si besoin)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier BANQUE introuvable : {fichier}")

    logger.info(f"Traitement BANQUE : {fichier.name}")

    lignes_detail = []
    nb_ignores    = 0

    # Cumul par contrat en centimes (int) pour éviter les flottants
    # ventes   = lignes DEBIT  source
    # rembours = lignes CREDIT source
    totaux = {cle: {"ventes": 0, "rembours": 0} for cle in CONTRATS.values()}

    with open(fichier, newline="", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")

        # ----------------------------------------------------------
        # 1. Lecture de la première ligne → date bancaire
        # ----------------------------------------------------------
        try:
            premiere_ligne = next(reader)
            date_raw = premiere_ligne[2].split("_")[0]
        except (StopIteration, IndexError):
            raise NotBanqueFileError(f"Fichier bancaire vide ou mal formé : {fichier.name}")

        date_ecriture = _parser_date_banque(date_raw)
        if not date_ecriture:
            raise NotBanqueFileError(f"Date bancaire non parseable : {date_raw!r}")

        date_banque_jjmmaa = _parser_date_banque_jjmmaa(date_raw)
        if not date_banque_jjmmaa:
            raise NotBanqueFileError(f"Date bancaire non parseable : {date_raw!r}")

        piece = f"JOURNEE DU {date_ecriture}"
        logger.debug(f"Date écriture banque : {date_ecriture}")
        logger.debug(f"Date banque format jjmmaa : {date_banque_jjmmaa}")

        # ----------------------------------------------------------
        # 2. Parcours des transactions
        # ----------------------------------------------------------
        for idx, row in enumerate(reader, start=2):

            if not row or len(row) < 9:
                logger.debug(f"Ligne {idx} ignorée : trop courte ({len(row)} colonnes)")
                nb_ignores += 1
                continue

            type_ligne = row[0].strip().upper()
            statut     = row[7].strip().upper()

            if type_ligne != "TRANSACTION":
                continue

            if statut != "CAPTURED":
                logger.debug(f"Ligne {idx} ignorée : statut {statut!r}")
                nb_ignores += 1
                continue

            commande       = row[3].strip().lstrip("M")
            contrat        = row[4].strip()
            sens_source    = row[5].strip().upper()
            montant_devise = int(row[6].strip())
            montant_eur    = montant_devise / 100

            # Contrat reconnu ?
            cle = CONTRATS.get(contrat)
            if not cle:
                logger.warning(f"Ligne {idx} ignorée : contrat inconnu {contrat!r}")
                nb_ignores += 1
                continue

            # --------------------------------------------------
            # Sens comptable lignes détail (inchangé) :
            #   DEBIT  source = vente        → C
            #   CREDIT source = remboursement → D
            # --------------------------------------------------
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

    # ----------------------------------------------------------
    # 3. Vérification
    # ----------------------------------------------------------
    if not lignes_detail:
        raise NotBanqueFileError(
            f"Aucune transaction CAPTURED trouvée dans {fichier.name}"
        )

    logger.info(
        f"{len(lignes_detail)} transactions traitées "
        f"({nb_ignores} lignes ignorées)"
    )

    # ----------------------------------------------------------
    # 4. Lignes de contrepartie bancaire
    #    VENTES        → D (débit)
    #    REMBOURSEMENTS → C (crédit)
    #    2 lignes séparées si les deux existent pour un même contrat
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

    logger.info(
        f"Export BANQUE : {sortie.name} "
        f"({len(lignes_detail + lignes_via)} écritures)"
    )
    return sortie
