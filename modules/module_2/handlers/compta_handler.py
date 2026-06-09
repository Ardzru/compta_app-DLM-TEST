"""
Module 2 - Handler COMPTA
Extraction des commandes depuis export comptable Sage.
"""

import pandas as pd
from pathlib import Path
from typing import Tuple, Optional
from config import logger
from core.utils.colonnes import trouver_colonnes
from core.utils.colonnes import (
    COMPTA_COLONNES,
    COMPTA_JOURNAUX_VE,
    COMPTA_JOURNAUX_ARGENT,
    PRO_PARTENAIRES,
)

# ==========================================================
# UTILITAIRES
# ==========================================================

def _get_engine(fichier: Path) -> str:
    """Détermine le moteur Excel selon l'extension."""
    return "openpyxl" if fichier.suffix.lower() == ".xlsx" else "xlrd"

def est_compta_internet(fichier: Path) -> bool:
    """
    Détecte un fichier compta Internet.
    Critères : nom contient "interr" ET colonnes standard présentes.
    """
    try:
        if "interr" not in fichier.name.lower():
            return False

        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, engine=engine, nrows=5)

        # Doit avoir au moins les colonnes clés
        cols_norm = {c.lower().strip() for c in df.columns}
        return any("libellé" in c or "libelle" in c for c in cols_norm)
    except:
        return False

# ==========================================================
# CHARGEMENT ET NORMALISATION
# ==========================================================

def charger_compta(fichier: Path) -> pd.DataFrame:
    """
    Charge le fichier compta et retourne un DataFrame normalisé.

    Colonnes en sortie :
    - date, num_commande, montant_signe, journal, debit, credit
    - num_piece, type_ecriture, est_pro, nom_partenaire

    SANS filtrage : on retourne TOUT, y compris les montants négatifs.
    Le filtrage se fait dans extraire_commandes().
    """
    try:
        engine = _get_engine(fichier)
        df = pd.read_excel(fichier, engine=engine, dtype=str)

        logger.info(f"[ComptaHandler] Fichier chargé : {len(df)} lignes")
        logger.debug(f"[ComptaHandler] Colonnes brutes : {list(df.columns)}")

        # ────────────────────────────────────────────────────────────────
        # ÉTAPE 1 : Détection des colonnes (flexible)
        # ────────────────────────────────────────────────────────────────

        mapping = {
            "date": ["date", "date de commande", "date d'écriture"],
            "libelle": ["libellé", "libelle", "libellé écriture", "objet"],
            "montant": ["montant signé", "montant", "total"],
            "journal": ["journal", "journal code"],
            "debit": ["débit", "debit"],
            "credit": ["crédit", "credit"],
            "num_piece": ["n° pièce", "n°pièce", "num pièce", "reference"],
        }

        colonnes = trouver_colonnes(df, mapping)

        logger.debug(f"[ComptaHandler] Colonnes détectées : {colonnes}")

        # Colonne A pour les numéros PRO
        col_a = df.iloc[:, 0] if len(df.columns) > 0 else pd.Series(dtype=str)

        # ────────────────────────────────────────────────────────────────
        # ÉTAPE 2 : Construction du DataFrame normalisé
        # ────────────────────────────────────────────────────────────────

        resultat = pd.DataFrame()

        # Date
        col_date = colonnes.get("date")
        if col_date:
            resultat["date"] = pd.to_datetime(df[col_date], errors="coerce")
        else:
            resultat["date"] = pd.NaT

        # Numéro de commande (depuis libellé)
        col_libelle = colonnes.get("libelle")
        if col_libelle:
            resultat["num_commande"] = df[col_libelle].astype(str).str.strip()
        else:
            resultat["num_commande"] = ""

        # Montant signé (peut être négatif, on le garde)
        col_montant = colonnes.get("montant")
        if col_montant:
            resultat["montant_signe"] = pd.to_numeric(df[col_montant], errors="coerce")
        else:
            resultat["montant_signe"] = 0.0

        # Journal
        col_journal = colonnes.get("journal")
        if col_journal:
            resultat["journal"] = df[col_journal].astype(str).str.strip().str.upper()
        else:
            resultat["journal"] = ""

        # Débit / Crédit
        col_debit = colonnes.get("debit")
        col_credit = colonnes.get("credit")
        if col_debit:
            resultat["debit"] = pd.to_numeric(df[col_debit], errors="coerce")
        else:
            resultat["debit"] = 0.0
        if col_credit:
            resultat["credit"] = pd.to_numeric(df[col_credit], errors="coerce")
        else:
            resultat["credit"] = 0.0

        # N° pièce
        col_piece = colonnes.get("num_piece")
        if col_piece:
            resultat["num_piece"] = df[col_piece].astype(str).str.strip()
        else:
            resultat["num_piece"] = ""

        # Type d'écriture
        def type_ecriture(j):
            if j in COMPTA_JOURNAUX_VE:
                return "VE"
            elif j in COMPTA_JOURNAUX_ARGENT:
                return "ARGENT_RECU"
            return "AUTRE"

        resultat["type_ecriture"] = resultat["journal"].apply(type_ecriture)

        # Détection PRO
        def get_pro(val):
            try:
                num = int(float(val))
                return PRO_PARTENAIRES.get(num, None)
            except:
                return None

        resultat["nom_partenaire"] = col_a.astype(str).str.strip().apply(get_pro)
        resultat["est_pro"] = resultat["nom_partenaire"].notna()

        logger.info(
            f"[ComptaHandler] {len(resultat)} lignes chargées | "
            f"PRO: {resultat['est_pro'].sum()} | "
            f"VE: {(resultat['type_ecriture'] == 'VE').sum()}"
        )

        return resultat

    except Exception as e:
        logger.error(f"[ComptaHandler] Erreur chargement {fichier.name} : {e}", exc_info=True)
        return pd.DataFrame()

# ==========================================================
# EXTRACTION DES COMMANDES
# ==========================================================

def extraire_commandes(df: pd.DataFrame) -> Tuple[dict, list]:
    """
    Extrait les commandes valides à partir du DataFrame normalisé.

    Retourne :
    - commandes (dict) : {num_commande: {montant, date, ...}}
    - rejetees (list)  : [{commande_raw, raison, ...}]

    Filtres appliqués :
    1. Numéro doit être 8 chiffres
    2. Montant doit être non-zéro
    """
    commandes = {}
    rejetees = []
    error_count = 0

    if df.empty:
        logger.warning("[ComptaHandler] DataFrame vide")
        return {}, []

    logger.info(f"[ComptaHandler] Extraction : {len(df)} lignes à traiter")

    for idx, row in df.iterrows():
        try:
            cmd = str(row.get("num_commande", "")).strip()
            montant = row.get("montant_signe", 0.0)
            date = row.get("date", "")

            # Filtre 1 : Format (8 chiffres)
            if not cmd or not cmd.isdigit() or len(cmd) != 8:
                rejetees.append({
                    "commande_raw": cmd,
                    "raison": "format invalide",
                    "montant": montant,
                    "date": str(date),
                })
                continue

            # Filtre 2 : Montant non-zéro
            try:
                montant = float(montant)
            except:
                montant = 0.0

            if montant == 0:
                rejetees.append({
                    "commande_raw": cmd,
                    "raison": "montant zéro",
                    "montant": montant,
                    "date": str(date),
                })
                continue

            # ✅ Agrégation
            if cmd not in commandes:
                commandes[cmd] = {
                    "montant": 0.0,
                    "date": str(date),
                    "journal": row.get("journal", ""),
                    "type_ecriture": row.get("type_ecriture", ""),
                    "est_pro": bool(row.get("est_pro", False)),
                    "nom_partenaire": row.get("nom_partenaire", None),
                }

            commandes[cmd]["montant"] += montant

        except Exception as e:
            error_count += 1
            logger.error(f"[ComptaHandler] Erreur ligne {idx}: {e}")
            rejetees.append({
                "commande_raw": str(row.get("num_commande", "?")),
                "raison": str(e),
            })

    logger.info(
        f"[ComptaHandler] Extraction : {len(commandes)} valides | "
        f"{len(rejetees)}/{len(df)} rejetées | {error_count} erreurs"
    )

    return commandes, rejetees

# ==========================================================
# POINT D'ENTREE POUR LE DISPATCHER
# ==========================================================

def traiter_compta(fichier: Path) -> Optional[pd.DataFrame]:
    """Point d'entrée pour le dispatcher."""
    logger.info(f"[MODULE2][START] traiter_compta : {fichier.name}")
    try:
        df = charger_compta(fichier)
        logger.info(f"[MODULE2][OK] {len(df)} lignes retournées")
        return df
    except Exception as e:
        logger.error(f"[MODULE2][FAIL] {e}", exc_info=True)
        return None

# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [
    "est_compta_internet",
    "charger_compta",
    "extraire_commandes",
    "traiter_compta",
]
