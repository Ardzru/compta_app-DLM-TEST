"""
Module 1 — Handler BANQUE
Traite fichiers bancaires CSV (format JT_DOMAINE...) → écritures comptables.

Structure réelle du fichier :
  Ligne TITRE  : [TITRE, nom_société, date_heure, TABLE_V_CUSTOM, ...]
  Ligne ENTETE : [ENTETE, Date du paiement, Date remise, Commande,
                  Contrat commerçant, Type, Montant total, Statut]
  Lignes DATA  : [TRANSACTION, 20260531, 20260603, 14044435,
                  8430996, DEBIT, 29300, CAPTURED]

Date d'écriture comptable = colonne C (index 2) = Date remise (format AAAAMMJJ)
"""

import csv
from pathlib import Path

import pandas as pd

from config import DOSSIER_SORTIE, logger
from core.utils.date import formater_date
from core.utils.montant import format_montant_compta
from core.utils.constantes import (
    STE_DLM,
    JOURNAL_CEBOOBA,
    COLONNES_SORTIE,
    COMPTE_TRANSIT,
    COL_STE,
    COL_DATE,
    COL_COMPTE,
    COL_AUX,
    COL_PIECE,
    COL_OBJET,
    COL_DEBIT,
    COL_CREDIT,
    COL_JOURNAL,
    COL_ANALYTIQUE,
    CONTRATS_BANQUE,
)

# ============================================================================
# INDICES COLONNES
# [TRANSACTION, date_paiement, date_remise, commande, contrat, type, montant, statut]
# ============================================================================
IDX_TYPE        = 0   # TRANSACTION / ENTETE / TITRE
IDX_DATE_PAIEM  = 1   # Date du paiement  (non utilisée pour l'écriture)
IDX_DATE_REMISE = 2   # ✅ Date remise AAAAMMJJ → date d'écriture comptable
IDX_COMMANDE    = 3   # numéro de commande → libellé détail
IDX_CONTRAT     = 4   # numéro contrat commerçant → CB/AMEX/PLANET
IDX_SENS        = 5   # DEBIT / CREDIT
IDX_MONTANT     = 6   # montant en centimes
IDX_STATUT      = 7   # CAPTURED / REFUSED...

NB_COLS_MIN     = 8

# ============================================================================
# EXCEPTION MÉTIER
# ============================================================================

class NotBanqueFileError(Exception):
    """Levée si aucune transaction bancaire exploitable n'est trouvée."""
    pass

# ============================================================================
# UTILITAIRES INTERNES
# ============================================================================

def _construire_libelle_contrepartie(cle: str, date_ecriture: str) -> str:
    """Construit le libellé normalisé pour les lignes de contrepartie."""
    labels = {
        "CB":     f"CB DOMAINE DE LOIS {date_ecriture}",
        "AMEX":   f"AMEX DU {date_ecriture}",
        "PLANET": f"PLANET DU {date_ecriture}",
    }
    return labels.get(cle, f"{cle} DU {date_ecriture}")

# ============================================================================
# HANDLER PRINCIPAL
# ============================================================================

def traiter_banque(fichier: Path) -> tuple[str, str]:
    """
    Traite un fichier bancaire CSV (format JT_DOMAINE_DE_LOISIRS...)
    et génère les écritures comptables.

    - Date d'écriture = colonne C (Date remise, format AAAAMMJJ)
    - Libellé détail  = numéro de commande (colonne D)
    - Contrepartie    = totaux par type CB/AMEX/PLANET
    """

    fichier = Path(fichier)
    if not fichier.exists():
        msg = f"Fichier BANQUE introuvable : {fichier}"
        logger.error(f"[BANQUE] {msg}")
        return "ERREUR", msg

    try:
        lignes_detail      = []
        date_ecriture      = None   # DD/MM/YYYY — pris sur la 1ère TRANSACTION valide
        nb_ignores         = 0
        nb_contrat_inconnu = 0
        contrats_inconnus  = set()

        totaux = {
            cle: {"ventes": 0, "remboursements": 0}
            for cle in set(CONTRATS_BANQUE.values())
        }

        with open(fichier, newline="", encoding="latin1") as f:
            reader = csv.reader(f, delimiter=";")

            for idx, row in enumerate(reader):

                if not row or not row[0].strip():
                    continue

                type_ligne = row[0].strip().upper()

                # ── Ignorer TITRE et ENTETE ─────────────────────────────
                if type_ligne in ("TITRE", "ENTETE"):
                    continue

                # ── Ignorer tout ce qui n'est pas TRANSACTION ───────────
                if type_ligne != "TRANSACTION":
                    nb_ignores += 1
                    continue

                if len(row) < NB_COLS_MIN:
                    logger.debug(
                        f"[BANQUE] Ligne {idx} trop courte ({len(row)} cols), ignorée"
                    )
                    nb_ignores += 1
                    continue

                statut      = row[IDX_STATUT].strip().upper()
                commande    = row[IDX_COMMANDE].strip()
                contrat_num = row[IDX_CONTRAT].strip()
                sens        = row[IDX_SENS].strip().upper()
                montant_str = row[IDX_MONTANT].strip()
                date_raw    = row[IDX_DATE_REMISE].strip()  # ✅ colonne C

                # ── Filtre statut ───────────────────────────────────────
                if statut != "CAPTURED":
                    nb_ignores += 1
                    continue

                # ── Date d'écriture : on la prend sur la 1ère ligne valide
                if date_ecriture is None:
                    date_ecriture = formater_date(date_raw)
                    if date_ecriture:
                        logger.debug(f"[BANQUE] Date écriture : {date_ecriture}")
                    else:
                        logger.warning(
                            f"[BANQUE] Date remise illisible ligne {idx} : {date_raw!r}"
                        )

                # ── Résolution contrat → clé métier ────────────────────
                cle_contrat = CONTRATS_BANQUE.get(contrat_num)
                if not cle_contrat:
                    contrats_inconnus.add(contrat_num)
                    nb_contrat_inconnu += 1
                    nb_ignores += 1
                    continue

                # ── Montant ─────────────────────────────────────────────
                try:
                    montant_centimes = int(montant_str)
                except ValueError:
                    logger.warning(
                        f"[BANQUE] Montant invalide ligne {idx} : {montant_str!r}, ignorée"
                    )
                    nb_ignores += 1
                    continue

                montant_eur = montant_centimes / 100

                # ── Sens comptable ──────────────────────────────────────
                # DEBIT source (vente client) → CREDIT en comptabilité
                if sens == "DEBIT":
                    d, c = "", format_montant_compta(montant_eur)
                    totaux[cle_contrat]["ventes"] += montant_centimes
                elif sens == "CREDIT":
                    d, c = format_montant_compta(montant_eur), ""
                    totaux[cle_contrat]["remboursements"] += montant_centimes
                else:
                    logger.warning(
                        f"[BANQUE] Sens inconnu ligne {idx} : {sens!r}, ignorée"
                    )
                    nb_ignores += 1
                    continue

                # ── Ligne détail ────────────────────────────────────────
                lignes_detail.append({
                    COL_OBJET:  commande,
                    COL_DEBIT:  d,
                    COL_CREDIT: c,
                })

        # ── Vérifications post-lecture ──────────────────────────────────
        if contrats_inconnus:
            logger.warning(
                f"[BANQUE] Contrats non reconnus ({nb_contrat_inconnu} lignes) : "
                f"{contrats_inconnus} — à ajouter dans CONTRATS_BANQUE si nécessaire"
            )

        if not lignes_detail:
            raise NotBanqueFileError("Aucune transaction CAPTURED exploitable")

        if not date_ecriture:
            raise NotBanqueFileError(
                "Date d'écriture introuvable (colonne C vide ou invalide)"
            )

        # ── Lignes de contrepartie (totaux par type) ────────────────────
        lignes_contrepartie = []
        for cle, valeurs in totaux.items():
            libelle = _construire_libelle_contrepartie(cle, date_ecriture)

            if valeurs["ventes"] > 0:
                lignes_contrepartie.append({
                    COL_OBJET:  libelle,
                    COL_DEBIT:  format_montant_compta(valeurs["ventes"] / 100),
                    COL_CREDIT: "",
                })

            if valeurs["remboursements"] > 0:
                lignes_contrepartie.append({
                    COL_OBJET:  libelle,
                    COL_DEBIT:  "",
                    COL_CREDIT: format_montant_compta(valeurs["remboursements"] / 100),
                })

        # ── Construction du DataFrame de sortie ─────────────────────────
        DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
        sortie = DOSSIER_SORTIE / f"{fichier.stem}_banque.csv"
        piece  = f"Encaissement du {date_ecriture}"

        donnees = []
        for ligne in lignes_detail + lignes_contrepartie:
            donnees.append({
                COL_STE:        STE_DLM,
                COL_DATE:       date_ecriture,
                COL_COMPTE:     COMPTE_TRANSIT,
                COL_AUX:        "",
                COL_PIECE:      piece,
                COL_OBJET:      ligne[COL_OBJET],
                COL_DEBIT:      ligne[COL_DEBIT],
                COL_CREDIT:     ligne[COL_CREDIT],
                COL_JOURNAL:    JOURNAL_CEBOOBA,
                COL_ANALYTIQUE: "",
            })

        df = pd.DataFrame(donnees, columns=COLONNES_SORTIE)
        df.to_csv(sortie, sep=";", index=False, encoding="latin-1")

        logger.info(
            f"[BANQUE] ✅ {len(lignes_detail)} transaction(s) | "
            f"{nb_ignores} ignorée(s) | date={date_ecriture} → {sortie.name}"
        )
        return "OK", str(sortie)

    except NotBanqueFileError as e:
        msg = str(e)
        logger.warning(f"[BANQUE] {msg}")
        return "AUCUNE_DONNEE", msg

    except Exception as e:
        msg = f"Erreur traitement BANQUE : {e}"
        logger.error(f"[BANQUE] {msg}", exc_info=True)
        return "ERREUR", msg

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ["traiter_banque", "NotBanqueFileError"]
