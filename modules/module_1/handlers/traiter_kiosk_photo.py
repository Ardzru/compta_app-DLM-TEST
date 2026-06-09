"""
Module 1 - Handler KIOSK_PHOTO
Traite les fichiers de ventes du kiosque photo et génère les écritures comptables
"""

from pathlib import Path
from typing import Optional
import pandas as pd

from config import DOSSIER_SORTIE
from config import logger
from core.moniteur_schema import comparer_schema
from core.utils.montant import format_montant_compta
from core.utils.constantes import (
    STE_DLM,
    COMPTE_VENTES,
    COMPTE_TVA_COLLECTEE,
    COMPTE_MONNAYEUR,
    COMPTE_TPE,
    JOURNAL_VE,
    ANALYTIQUE_VIDE,
    COL_STE, COL_DATE, COL_COMPTE, COL_AUX,
    COL_PIECE, COL_OBJET, COL_DEBIT, COL_CREDIT,
    COL_JOURNAL, COL_ANALYTIQUE,
    COLONNES_SORTIE,
)

# ==========================================================
# EXCEPTION MÉTIER
# ==========================================================

class NotKioskPhotoFileError(Exception):
    """Levée si aucune vente kiosque photo exploitable n'est trouvée."""
    pass

# ==========================================================
# COLONNES ATTENDUES
# ==========================================================
_COL_DATE    = "dateheure"
_COL_MONTANT = "montant"
_COL_VENDEUR = "vendeur"

_COLONNES_REQUISES = [_COL_DATE, _COL_MONTANT, _COL_VENDEUR]

# ==========================================================
# CONSTANTES MÉTIER
# ==========================================================
_TAUX_TVA = 1.20

_ANALYTIQUE_CA  = "AD-CO14-XX"
_ANALYTIQUE_ENC = ""

# ==========================================================
# UTILITAIRES INTERNES
# ==========================================================

def _formater_date(val) -> Optional[str]:
    """
    Formate une date au format JJ/MM/AAAA.

    Retourne None si la date est invalide.
    """
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        logger.warning(f"[KIOSK] Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d/%m/%Y")


def _lire_fichier(fichier: Path) -> pd.DataFrame:
    """
    Lit le fichier source selon son extension.

    - .csv → pd.read_csv avec séparateur ";"
    - autres → pd.read_excel
    """
    ext = fichier.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(fichier, sep=";", encoding="utf-8")
    return pd.read_excel(fichier, engine="openpyxl")


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
        raise ValueError(msg)

# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_kiosk_photo(fichier: Path) -> tuple[str, str]:
    """
    Traite un fichier de ventes du kiosque photo (luge)
    et génère les écritures comptables correspondantes.

    Logique métier :
    - Les ventes JETON sont exclues
    - TVA à 20 % calculée sur le TTC
    - Encaissements ventilés : MONNAYEUR (580001) / TPE (580005)

    Retourne:
        ("OK", chemin_fichier) | ("ERREUR", message)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        msg = f"Fichier kiosque photo introuvable : {fichier}"
        logger.error(f"[KIOSK] {msg}")
        return "ERREUR", msg

    logger.info(f"[MODULE1][KIOSK] Début traitement : {fichier.name}")

    try:
        # ----------------------------------------------------------
        # 1. Lecture + validation schéma
        # ----------------------------------------------------------
        df = _lire_fichier(fichier)

        if df.empty:
            msg = f"Fichier vide : {fichier.name}"
            logger.warning(f"[KIOSK] {msg}")
            return "ERREUR", msg

        comparer_schema(df, "kiosk_photo")
        _verifier_colonnes(df, fichier)

        # ----------------------------------------------------------
        # 2. Parcours des ventes
        # ----------------------------------------------------------
        total_ttc       = 0.0
        total_monnayeur = 0.0
        total_tpe       = 0.0
        date_journee    = None
        nb_ignores      = 0

        for idx, row in df.iterrows():

            # Date de journée = première ligne valide
            if date_journee is None:
                date_journee = _formater_date(row[_COL_DATE])

            montant_raw = row[_COL_MONTANT]

            if pd.isna(montant_raw):
                nb_ignores += 1
                continue

            montant = float(montant_raw)

            if montant == 0:
                nb_ignores += 1
                continue

            vendeur = str(row[_COL_VENDEUR]).strip().upper()

            # Ventes jetons exclues
            if "JETON" in vendeur:
                logger.debug(f"[KIOSK] Ligne {idx} ignorée : vente JETON")
                nb_ignores += 1
                continue

            total_ttc += montant

            if "MONNAYEUR" in vendeur:
                total_monnayeur += montant
            elif "TPE" in vendeur:
                total_tpe += montant
            else:
                logger.warning(
                    f"[KIOSK] Ligne {idx} : vendeur non catégorisé {vendeur!r}, "
                    f"comptabilisé en TTC uniquement"
                )

        # ----------------------------------------------------------
        # 3. Vérification
        # ----------------------------------------------------------
        if total_ttc == 0:
            msg = f"Aucune vente kiosque photo exploitable dans {fichier.name}"
            logger.warning(f"[KIOSK] {msg}")
            return "ERREUR", msg

        if not date_journee:
            msg = f"Impossible de déterminer la date de journée dans {fichier.name}"
            logger.warning(f"[KIOSK] {msg}")
            return "ERREUR", msg

        logger.info(
            f"[KIOSK] TTC={total_ttc:.2f}€ "
            f"Monnayeur={total_monnayeur:.2f}€ "
            f"TPE={total_tpe:.2f}€ "
            f"({nb_ignores} lignes ignorées)"
        )

        # ----------------------------------------------------------
        # 4. Calculs comptables
        # ----------------------------------------------------------
        ht  = round(total_ttc / _TAUX_TVA, 2)
        tva = round(total_ttc - ht, 2)

        piece = f"JOURNEE DU {date_journee}"

        # ----------------------------------------------------------
        # 5. Construction des écritures
        # ----------------------------------------------------------
        lignes_finales = [
            # Produit CA HT
            {
                COL_STE:        STE_DLM,
                COL_DATE:       date_journee,
                COL_COMPTE:     COMPTE_VENTES,
                COL_AUX:        ANALYTIQUE_VIDE,
                COL_PIECE:      piece,
                COL_OBJET:      f"{piece} LUGE",
                COL_DEBIT:      "",
                COL_CREDIT:     format_montant_compta(ht),
                COL_JOURNAL:    JOURNAL_VE,
                COL_ANALYTIQUE: _ANALYTIQUE_CA,
            },
            # TVA collectée
            {
                COL_STE:        STE_DLM,
                COL_DATE:       date_journee,
                COL_COMPTE:     COMPTE_TVA_COLLECTEE,
                COL_AUX:        ANALYTIQUE_VIDE,
                COL_PIECE:      piece,
                COL_OBJET:      f"TVA {piece} LUGE",
                COL_DEBIT:      "",
                COL_CREDIT:     format_montant_compta(tva),
                COL_JOURNAL:    JOURNAL_VE,
                COL_ANALYTIQUE: ANALYTIQUE_VIDE,
            },
        ]

        # Encaissement monnayeur
        if total_monnayeur > 0:
            lignes_finales.append({
                COL_STE:        STE_DLM,
                COL_DATE:       date_journee,
                COL_COMPTE:     COMPTE_MONNAYEUR,
                COL_AUX:        ANALYTIQUE_VIDE,
                COL_PIECE:      piece,
                COL_OBJET:      f"{piece} LUGE - MONNAYEUR",
                COL_DEBIT:      format_montant_compta(total_monnayeur),
                COL_CREDIT:     "",
                COL_JOURNAL:    JOURNAL_VE,
                COL_ANALYTIQUE: _ANALYTIQUE_ENC,
            })

        # Encaissement TPE
        if total_tpe > 0:
            lignes_finales.append({
                COL_STE:        STE_DLM,
                COL_DATE:       date_journee,
                COL_COMPTE:     COMPTE_TPE,
                COL_AUX:        ANALYTIQUE_VIDE,
                COL_PIECE:      piece,
                COL_OBJET:      f"{piece} LUGE - TPE",
                COL_DEBIT:      format_montant_compta(total_tpe),
                COL_CREDIT:     "",
                COL_JOURNAL:    JOURNAL_VE,
                COL_ANALYTIQUE: _ANALYTIQUE_ENC,
            })

        # ----------------------------------------------------------
        # 6. Export CSV
        # ----------------------------------------------------------
        DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

        df_final = pd.DataFrame(lignes_finales, columns=COLONNES_SORTIE)
        sortie   = DOSSIER_SORTIE / f"{fichier.stem}_kiosk_photo.csv"
        df_final.to_csv(sortie, sep=";", index=False, encoding="latin-1")

        logger.info(
            f"[MODULE1][KIOSK] Export réussi : {sortie.name} ({len(lignes_finales)} écritures)"
        )
        return "OK", str(sortie)

    except ValueError as e:
        msg = f"Erreur validation : {e}"
        logger.error(f"[KIOSK] {msg}")
        return "ERREUR", msg

    except Exception as e:
        msg = f"Erreur de traitement : {e}"
        logger.error(f"[KIOSK] {msg}", exc_info=True)
        return "ERREUR", msg


# ==========================================================
__all__ = ["traiter_kiosk_photo", "NotKioskPhotoFileError"]
