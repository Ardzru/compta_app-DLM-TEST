import csv
from pathlib import Path
from typing import Optional
from config import DOSSIER_SORTIE
from config import logger
from core.utils.montant import to_float, format_montant
from core.utils.colonnes import STE_DEFAUT, JOURNAUX, CONTRATS_AMEX, COLONNES_SORTIE


# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotBanqueFileError(Exception):
    """Levée si aucune transaction bancaire exploitable n'est trouvée."""
    pass


# ==========================================================
# UTILITAIRES PRIVÉS
# ==========================================================

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
        annee = f"20{annee_court}"
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
    - CB     : date J   (sans -1) dans le libellé
    - AMEX   : date J-1 dans le libellé
    - PLANET : date J-1 dans le libellé
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier BANQUE introuvable : {fichier}")

    logger.info(f"Traitement BANQUE : {fichier.name}")

    lignes_detail = []
    nb_ignores = 0

    # Cumul par contrat en centimes (int) pour éviter les flottants
    # ventes   = lignes DEBIT  source
    # rembours = lignes CREDIT source
    totaux = {cle: {"ventes": 0, "rembours": 0} for cle in CONTRATS_AMEX.values()}

    with open(fichier, newline="", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")

        # ----------------------------------------------------------
        # 1. Lecture de la première ligne → date bancaire
        # ----------------------------------------------------------
        try:
            premiere_ligne = next(reader)
            date_raw = premiere_ligne[0].strip()
            date_ecriture = _parser_date_banque(date_raw)  # J-1 → AMEX / PLANET
            date_banque_jjmmaa = _parser_date_banque_jjmmaa(date_raw)  # J   → CB libellé
            piece = premiere_ligne[1].strip() if len(premiere_ligne) > 1 else ""
        except StopIteration:
            raise NotBanqueFileError(f"Fichier vide : {fichier.name}")

        if not date_ecriture:
            raise NotBanqueFileError(f"Date invalide en première ligne : {fichier.name}")

        # ----------------------------------------------------------
        # 2. Lecture des lignes de transaction
        # ----------------------------------------------------------
        for idx, row in enumerate(reader, start=2):
            if len(row) < 7:
                nb_ignores += 1
                continue

            type_ligne = row[0].strip().upper()
            statut = row[2].strip().upper()

            if type_ligne != "TRANSACTION":
                nb_ignores += 1
                continue

            if statut != "CAPTURED":
                logger.debug(f"Ligne {idx} ignorée : statut {statut!r}")
                nb_ignores += 1
                continue

            commande = row[3].strip().lstrip("M")
            contrat = row[4].strip()
            sens_source = row[5].strip().upper()
            montant_devise = int(row[6].strip())
            montant_eur = montant_devise / 100

            # Contrat reconnu ?
            cle = CONTRATS_AMEX.get(contrat)
            if not cle:
                logger.warning(f"Ligne {idx} ignorée : contrat inconnu {contrat!r}")
                nb_ignores += 1
                continue

            # --------------------------------------------------
            # Sens comptable lignes détail :
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
                "d": d,
                "c": c,
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
    #    VENTES         → D (débit)
    #    REMBOURSEMENTS → C (crédit)
    #    2 lignes séparées si les deux existent pour un même contrat
    # ----------------------------------------------------------
    lignes_via = []

    for cle, valeurs in totaux.items():

        total_ventes = valeurs["ventes"]
        total_rembours = valeurs["rembours"]

        libelle = _construire_libelle_banque(cle, date_ecriture, date_banque_jjmmaa)

        if total_ventes > 0:
            montant_vente = total_ventes / 100
            lignes_via.append({
                "objet": libelle,
                "d": format_montant(montant_vente),
                "c": "",
            })
            logger.debug(f"Contrepartie VENTE {cle} : {format_montant(montant_vente)} D")

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

        writer.writerow(COLONNES_SORTIE)

        for l in lignes_detail + lignes_via:
            writer.writerow([
                STE_DEFAUT, date_ecriture, "580010DS5", "",
                piece, l["objet"], l["d"], l["c"],
                JOURNAUX["banque"], "",
            ])

    logger.info(
        f"Export BANQUE : {sortie.name} "
        f"({len(lignes_detail + lignes_via)} écritures)"
    )
    return sortie


# ==========================================================
# CLASSE HANDLER
# ==========================================================

class TraiterBanqueHandler:
    """Handler pour traiter les fichiers banque."""

    @staticmethod
    def traiter(fichier: Path) -> None:
        """Traite un fichier banque."""
        traiter_banque(fichier)

    @staticmethod
    def peut_traiter(detecteur_result: dict) -> bool:
        """Vérifie si c'est un fichier banque."""
        return detecteur_result.get("type") == "banque"


__all__ = ['TraiterBanqueHandler', 'traiter_banque']
