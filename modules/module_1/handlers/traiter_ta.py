"""
Module 1 - Handler TA
Traite les fichiers de trésorerie assistée (billetterie/caisse)
et génère les écritures comptables
"""

from pathlib import Path
import re
import pandas as pd

from config import DOSSIER_SORTIE
from config import logger
from core.utils.montant import format_montant_compta
from core.utils.constantes import (
    STE_DLM,
    COMPTE_TRANSIT,
    JOURNAL_VE,
    ANALYTIQUE_VIDE,
    COL_STE, COL_DATE, COL_COMPTE, COL_AUX,
    COL_PIECE, COL_OBJET, COL_DEBIT, COL_CREDIT,
    COL_JOURNAL, COL_ANALYTIQUE,
    COLONNES_SORTIE,
    TA_COL,
    TA_CAISSES_AUTORISEES,
    TA_LIBELLES_VENTES,
    TA_LIBELLES_ANNULATIONS,
)

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotTAFileError(Exception):
    """Levée si aucune ligne TA exploitable n'est trouvée."""
    pass

# ==========================================================
# COLONNES ATTENDUES (depuis TA_COL du core)
# ==========================================================
_COL_DATE     = TA_COL["date"]       # "DATE"
_COL_COMMANDE = TA_COL["commande"]   # "VALEUR PROMPT"
_COL_CAISSE   = TA_COL["caisse"]     # "CAISSE"
_COL_MONTANT  = TA_COL["montant"]    # "MONTANT"
_COL_LIBELLE  = TA_COL["libelle"]    # "SZNAME"

_COLONNES_REQUISES = [_COL_DATE, _COL_COMMANDE, _COL_CAISSE, _COL_MONTANT, _COL_LIBELLE]

# ==========================================================
# UTILITAIRES INTERNES
# ==========================================================

def _nettoyer_commande(val) -> str | None:
    """
    Extrait et normalise le numéro de commande.

    - Conserve uniquement les chiffres
    - Nécessite au moins 8 chiffres
    - Retourne les 8 premiers chiffres
    """
    if pd.isna(val):
        return None
    chiffres = re.findall(r"\d", str(val))
    if len(chiffres) < 8:
        return None
    return "".join(chiffres[:8])


def _formater_date(val) -> str | None:
    """
    Formate une date au format JJ/MM/AAAA.

    Retourne None si la date est invalide.
    """
    try:
        d = pd.to_datetime(val, errors="coerce")
        if pd.isna(d):
            logger.warning(f"[TA] Date invalide ignorée : {val!r}")
            return None
        return d.strftime("%d/%m/%Y")
    except Exception as e:
        logger.warning(f"[TA] Erreur formatage date {val!r} : {e}")
        return None


def _verifier_colonnes(df: pd.DataFrame, fichier: Path) -> None:
    """
    Vérifie que les colonnes attendues sont présentes.

    Lève ValueError si colonnes manquantes.
    """
    manquantes = [c for c in _COLONNES_REQUISES if c not in df.columns]
    if manquantes:
        msg = (
            f"Colonnes manquantes dans {fichier.name} : {manquantes}\n"
            f"Colonnes trouvées : {list(df.columns)}"
        )
        logger.error(f"[TA] {msg}")
        raise ValueError(msg)

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_ta(fichier: Path) -> tuple[str, str]:
    """
    Traite un fichier TA (billetterie / caisse) et génère
    les écritures comptables correspondantes.

    Règles métier :
    - Seules les caisses autorisées (72, 73, 77) sont traitées
    - Ventes → Débit 580010DS5
    - Annulations → Crédit 580010DS5
    - Contrepartie par caisse (diff ventes - annulations)

    Retourne:
        ("OK", chemin_fichier) | ("ERREUR", message)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        msg = f"Fichier TA introuvable : {fichier}"
        logger.error(f"[TA] {msg}")
        return "ERREUR", msg

    logger.info(f"[MODULE1][TA] Début traitement : {fichier.name}")

    try:
        # ----------------------------------------------------------
        # 1. Lecture Excel
        # ----------------------------------------------------------
        try:
            df = pd.read_excel(fichier)
        except Exception as e:
            msg = f"Impossible de lire {fichier.name} : {e}"
            logger.error(f"[TA] {msg}")
            raise NotTAFileError(msg)

        # ✅ CORRECTION : len(df) au lieu de if df
        if len(df) == 0:
            msg = f"Fichier vide : {fichier.name}"
            logger.warning(f"[TA] {msg}")
            raise NotTAFileError(msg)

        # Vérification des colonnes
        _verifier_colonnes(df, fichier)

        # ----------------------------------------------------------
        # 2. Parcours des lignes
        # ----------------------------------------------------------
        commandes: dict = {}  # { num_commande: {"date": str, "D": float, "C": float} }
        caisses: dict = {}    # { caisse: {"ventes": float, "annulations": float} }
        date_source: str | None = None
        nb_ignores = 0

        for idx, row in df.iterrows():

            # Date de journée = première date valide rencontrée
            if date_source is None and not pd.isna(row[_COL_DATE]):
                date_source = _formater_date(row[_COL_DATE])

            # Filtrage caisse
            caisse = str(row[_COL_CAISSE]).strip() if not pd.isna(row[_COL_CAISSE]) else ""
            if caisse not in TA_CAISSES_AUTORISEES:
                logger.debug(f"[TA] Ligne {idx} : caisse non autorisée {caisse!r}")
                nb_ignores += 1
                continue

            # Numéro de commande
            commande = _nettoyer_commande(row[_COL_COMMANDE])
            if not commande:
                logger.debug(f"[TA] Ligne {idx} : commande invalide {row[_COL_COMMANDE]!r}")
                nb_ignores += 1
                continue

            # Montant
            montant_raw = row[_COL_MONTANT]
            if pd.isna(montant_raw):
                logger.debug(f"[TA] Ligne {idx} : montant manquant")
                nb_ignores += 1
                continue

            try:
                montant = float(montant_raw)
            except (ValueError, TypeError):
                logger.debug(f"[TA] Ligne {idx} : montant invalide {montant_raw!r}")
                nb_ignores += 1
                continue

            libelle = str(row[_COL_LIBELLE]).strip() if not pd.isna(row[_COL_LIBELLE]) else ""

            # Initialisation des accumulateurs
            commandes.setdefault(commande, {"date": date_source, "D": 0.0, "C": 0.0})
            caisses.setdefault(caisse, {"ventes": 0.0, "annulations": 0.0})

            # Catégorisation
            if libelle in TA_LIBELLES_VENTES:
                commandes[commande]["D"] += montant
                caisses[caisse]["ventes"] += montant

            elif libelle in TA_LIBELLES_ANNULATIONS:
                commandes[commande]["C"] += montant
                caisses[caisse]["annulations"] += montant

            else:
                logger.debug(f"[TA] Ligne {idx} : libellé non catégorisé {libelle!r}")
                nb_ignores += 1

        # ----------------------------------------------------------
        # 3. Vérification
        # ----------------------------------------------------------
        if not commandes:
            msg = f"Aucune ligne TA exploitable dans {fichier.name}"
            logger.warning(f"[TA] {msg}")
            raise NotTAFileError(msg)

        if not date_source:
            msg = f"Impossible de déterminer la date de journée dans {fichier.name}"
            logger.warning(f"[TA] {msg}")
            raise NotTAFileError(msg)

        logger.info(
            f"[TA] Lecture complète : {len(commandes)} commandes, "
            f"{len(caisses)} caisses, {nb_ignores} lignes ignorées"
        )

        # ----------------------------------------------------------
        # 4. Construction des écritures comptables
        # ----------------------------------------------------------
        piece = f"JOURNEE DU {date_source}"
        lignes_finales = []
        total_debit = 0.0
        total_credit = 0.0

        # Écritures par commande
        for commande, data in commandes.items():

            if data["D"] > 0:
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       data["date"],
                    COL_COMPTE:     COMPTE_TRANSIT,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      piece,
                    COL_OBJET:      commande,
                    COL_DEBIT:      format_montant_compta(data["D"]),
                    COL_CREDIT:     "",
                    COL_JOURNAL:    JOURNAL_VE,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })
                total_debit += data["D"]

            if data["C"] > 0:
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       data["date"],
                    COL_COMPTE:     COMPTE_TRANSIT,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      piece,
                    COL_OBJET:      commande,
                    COL_DEBIT:      "",
                    COL_CREDIT:     format_montant_compta(data["C"]),
                    COL_JOURNAL:    JOURNAL_VE,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })
                total_credit += data["C"]

        # Écritures de contrepartie par caisse
        for caisse, totaux in sorted(caisses.items()):

            diff = totaux["ventes"] - totaux["annulations"]

            if diff == 0:
                logger.debug(f"[TA] Caisse {caisse} équilibrée, pas de contrepartie")
                continue

            objet = f"JOURNEE DU {date_source.replace('/', '-')} CAISSE {caisse}"

            if diff > 0:
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_source,
                    COL_COMPTE:     COMPTE_TRANSIT,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      piece,
                    COL_OBJET:      objet,
                    COL_DEBIT:      "",
                    COL_CREDIT:     format_montant_compta(diff),
                    COL_JOURNAL:    JOURNAL_VE,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })
                total_credit += diff
            else:
                lignes_finales.append({
                    COL_STE:        STE_DLM,
                    COL_DATE:       date_source,
                    COL_COMPTE:     COMPTE_TRANSIT,
                    COL_AUX:        ANALYTIQUE_VIDE,
                    COL_PIECE:      piece,
                    COL_OBJET:      objet,
                    COL_DEBIT:      format_montant_compta(abs(diff)),
                    COL_CREDIT:     "",
                    COL_JOURNAL:    JOURNAL_VE,
                    COL_ANALYTIQUE: ANALYTIQUE_VIDE,
                })
                total_debit += abs(diff)

        # ----------------------------------------------------------
        # 5. Export CSV
        # ----------------------------------------------------------
        DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

        df_final = pd.DataFrame(lignes_finales, columns=COLONNES_SORTIE)
        sortie = DOSSIER_SORTIE / f"{fichier.stem}_ta.csv"
        df_final.to_csv(sortie, sep=";", index=False, encoding="latin-1")

        logger.info(
            f"[MODULE1][TA] Export réussi : {sortie.name} "
            f"({len(lignes_finales)} écritures, "
            f"D={format_montant_compta(total_debit)} / "
            f"C={format_montant_compta(total_credit)})"
        )
        return "OK", str(sortie)

    except NotTAFileError as e:
        msg = str(e)
        logger.error(f"[TA] {msg}")
        return "ERREUR", msg

    except Exception as e:
        msg = f"Erreur de traitement : {e}"
        logger.error(f"[TA] {msg}", exc_info=True)
        return "ERREUR", msg


# ==========================================================
__all__ = ["traiter_ta", "NotTAFileError"]
