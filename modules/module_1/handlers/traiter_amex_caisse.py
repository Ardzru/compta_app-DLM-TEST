"""
Module 1 — Handler AMEX CAISSE
Traite fichiers AMEX CAISSE (.xlsx) → écritures comptables CSV.

Logique de regroupement :
- 580011 (virement) : regroupé par (date, caisse)
- 627800 (frais) : regroupé par date UNIQUEMENT (UNE SEULE ligne par date)
- 512121 (banque) : UNE SEULE ligne par date
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Dict, Optional, Tuple

from config import DOSSIER_SORTIE, FICHIER_CORRESPONDANCE_AMEX, logger
from core.moniteur_schema import comparer_schema
from core.utils.montant import format_montant_compta
from core.utils.date import formater_date_fr
from core.utils.constantes import (
    STE_DLM,
    JOURNAL_CAA,
    COLONNES_SORTIE,
    COMPTE_AMEX_CAISSE_TRANSIT,  # "580011"
    COMPTE_FRAIS_CB,             # "627800"
    COMPTE_BANQUE_AMEX_CAISSE,   # "512121"
    COMPTE_CLIENT,               # "411000"
    ANALYTIQUE_FRAIS_CB,         # "AD-CO00-XX"
)

# ============================================================
# INDICES DES COLONNES
# ============================================================

COL_DATE_REGLEMENT   = 1   # Date de règlement      (ex: 02/02/2026)
COL_DATE_TRANSACTION = 14  # Date de transaction    (ex: 29/01/2026)
COL_TYPE             = 4   # Type                   (SOC/ROC)
COL_NUM_REF          = 3   # Numéro de référence    (ex: 20853)
COL_NUM_REGLEMENT    = 2   # Numéro de règlement    (ex: 4903025623)
COL_MONTANT_BRUT     = 20  # Total des opérations   (ex: 1.235,50)
COL_FRAIS            = 23  # Montant de la remise   (ex: 12,36-)
COL_MONTANT_NET      = 26  # Montant du règlement   (ex: 1.223,14)
COL_ROC_ID_TERMINAL  = 7   # ID Terminal AMEX       (ex: SCA85E05)

# ============================================================
# UTILITAIRES PRIVÉS
# ============================================================

def _nettoyer_montant(val) -> float:
    """Nettoie et convertit un montant AMEX en float.
    Gère le format français : '1.235,50' et le signe suffixe '12,36-'
    """
    if pd.isna(val):
        return 0.0

    s = str(val).strip()
    s = s.replace(" ", "")

    # Signe négatif en suffixe → préfixe
    negatif = s.endswith("-")
    if negatif:
        s = s[:-1]

    # Format français : point = milliers, virgule = décimales
    s = s.replace(".", "").replace(",", ".")

    try:
        result = float(s)
        return -result if negatif else result
    except ValueError:
        return 0.0


def _date_en_cle(val) -> Optional[str]:
    """Retourne la date au format YYYYMMDD pour le n° pièce."""
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        return None
    return d.strftime("%Y%m%d")


def _generer_libelle_transit(date_transaction: str, num_caisse: str) -> str:
    """
    Génère le libellé pour le compte 580011 :
    'Journee du JJ-MM-AAAA caisse XX'
    date_transaction est au format DD/MM/YYYY (retourné par formater_date_fr)
    → on convertit en JJ-MM-AAAA via remplacement / par -
    """
    date_tirets = date_transaction.replace("/", "-")
    return f"Journee du {date_tirets} caisse {num_caisse}"


def _generer_libelle_banque(date_transaction: str) -> str:
    """Génère le libellé banque : 'AMEX CAISSE DU DD/MM/YYYY'"""
    return f"AMEX CAISSE DU {date_transaction}"


def _generer_libelle_detail(date_transaction: str, num_caisse: str) -> str:
    """Génère le libellé détail : 'AMEX CAISSE DU DD/MM/YYYY CAISSE XX'"""
    return f"AMEX CAISSE DU {date_transaction} CAISSE {num_caisse}"


def _generer_libelle_frais(date_transaction: str) -> str:
    """Génère le libellé frais : 'FRAIS AMEX - AMEX CAISSE DU DD/MM/YYYY'"""
    return f"FRAIS AMEX - AMEX CAISSE DU {date_transaction}"


# ============================================================
# CORRESPONDANCE TERMINAUX
# ============================================================

def _charger_correspondance(fichier: Path) -> Dict[str, Dict[str, str]]:
    """Charge le fichier de correspondance ID Terminal → N° de caisse."""
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier correspondance AMEX introuvable : {fichier}")

    try:
        df = pd.read_csv(fichier, sep=",", encoding="utf-8", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]

        correspondance = {}
        for _, row in df.iterrows():
            id_terminal = str(row["id_terminal"]).strip()

            if not id_terminal or id_terminal.lower() == "nan":
                continue

            correspondance[id_terminal] = {
                "caisse": str(row["numero_caisse"]).strip(),
                "compte": str(row["compte_comptable"]).strip(),
            }

        return correspondance

    except KeyError as e:
        logger.error(f"Colonne manquante dans correspondance AMEX : {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur chargement correspondance AMEX : {e}")
        raise


def _construire_map_soc_terminal(df: pd.DataFrame) -> Dict[int, str]:
    """
    Parcourt le DataFrame et associe chaque SOC (par son index)
    à l'ID Terminal du premier ROC enfant trouvé.
    """
    map_soc_terminal = {}
    current_soc_idx = None

    for idx, row in df.iterrows():
        type_ligne = str(row[COL_TYPE]).strip().upper()

        if type_ligne == "SOC":
            current_soc_idx = idx

        elif type_ligne == "ROC" and current_soc_idx is not None:
            if current_soc_idx not in map_soc_terminal:
                id_terminal = str(row[COL_ROC_ID_TERMINAL]).strip()
                if id_terminal and id_terminal.lower() != "nan":
                    map_soc_terminal[current_soc_idx] = id_terminal

    return map_soc_terminal


# ============================================================
# HANDLER PRINCIPAL
# ============================================================

def traiter_amex_caisse(fichier: Path) -> Tuple[str, str]:
    """
    Traite un fichier AMEX caisse (.xlsx) → écritures comptables CSV.

    Logique de regroupement :
    - 580011 (virement) : par (date, caisse)   ← libellé "Journee du JJ-MM-AAAA caisse XX"
    - 627800 (frais) : par date uniquement     ← UNE SEULE ligne par date
    - 512121 (banque) : UNE ligne par date     ← "AMEX CAISSE DU DD/MM/YYYY"
    """

    fichier = Path(fichier)
    if not fichier.exists():
        msg = f"Fichier AMEX caisse introuvable : {fichier}"
        logger.error(f"[AMEX_CAISSE] ❌ {msg}")
        raise FileNotFoundError(msg)

    # ----------------------------------------------------------
    # 1. Lecture du fichier
    # ----------------------------------------------------------
    try:
        df = pd.read_excel(fichier, header=None, engine="openpyxl")
    except Exception as e:
        msg = f"Impossible de lire {fichier.name} : {e}"
        logger.error(f"[AMEX_CAISSE] ❌ {msg}", exc_info=True)
        return "ERREUR", msg

    # ----------------------------------------------------------
    # 2. Vérification du schéma
    # ----------------------------------------------------------
    try:
        comparer_schema(df, "amex_caisse")
    except Exception as e:
        msg = f"Schéma invalide : {e}"
        logger.error(f"[AMEX_CAISSE] ❌ {msg}")
        return "ERREUR", msg

    # ----------------------------------------------------------
    # 3. Chargement de la correspondance terminaux
    # ----------------------------------------------------------
    try:
        correspondance = _charger_correspondance(FICHIER_CORRESPONDANCE_AMEX)
    except FileNotFoundError as e:
        return "ERREUR", str(e)

    # ----------------------------------------------------------
    # 4. Construction du lien SOC → ID Terminal via les ROC
    # ----------------------------------------------------------
    map_soc_terminal = _construire_map_soc_terminal(df)

    # ----------------------------------------------------------
    # 5. Accumulation par type de compte
    # ----------------------------------------------------------

    # 580011 : regroupé par (date, caisse)
    virements_par_caisse = defaultdict(lambda: {"lignes": [], "total": 0.0})

    # 627800 : regroupé par date UNIQUEMENT (UNE SEULE ligne par date)
    frais_par_date = defaultdict(float)

    # 512121 : regroupé par date
    banque_par_date = defaultdict(float)

    for idx, row in df.iterrows():

        # Filtrer uniquement les SOC
        if str(row[COL_TYPE]).strip().upper() != "SOC":
            continue

        # Dates
        date_reglement_raw   = row[COL_DATE_REGLEMENT]
        date_transaction_raw = row[COL_DATE_TRANSACTION]

        date_compta      = formater_date_fr(date_reglement_raw)
        date_transaction = formater_date_fr(date_transaction_raw)

        if not date_compta or not date_transaction:
            logger.warning(f"[AMEX_CAISSE] Ligne {idx} ignorée : date invalide")
            continue

        # Montants
        montant_brut = _nettoyer_montant(row[COL_MONTANT_BRUT])
        frais        = _nettoyer_montant(row[COL_FRAIS])
        montant_net  = _nettoyer_montant(row[COL_MONTANT_NET])

        # ID Terminal → caisse
        id_terminal = map_soc_terminal.get(idx, "")
        info_caisse = correspondance.get(id_terminal, {})
        num_caisse  = info_caisse.get("caisse", "INCONNUE")

        # N° pièce
        cle_date = _date_en_cle(date_reglement_raw)
        n_piece  = f"AMEX-{cle_date}"

        # ─────────────────────────────────────────────────────
        # CAS 1 : REMBOURSEMENT (montant_brut < 0)
        # ─────────────────────────────────────────────────────
        if montant_brut < 0:
            # 411000 → libellé détail classique
            libelle_client = _generer_libelle_detail(date_transaction, num_caisse)

            virements_par_caisse[(date_compta, num_caisse)]["lignes"].append({
                "STE":        STE_DLM,
                "DATE":       date_compta,
                "COMPTE":     COMPTE_CLIENT,
                "Auxiliaire": "",
                "n°pièce":    n_piece,
                "OBJET":      libelle_client,
                "D":          format_montant_compta(montant_brut),
                "C":          "",
                "Journal":    JOURNAL_CAA,
                "Analytique": "",
            })

        # ─────────────────────────────────────────────────────
        # CAS 2 : ENCAISSEMENT (montant_brut >= 0)
        # ─────────────────────────────────────────────────────
        else:
            # 580011 → libellé spécifique "Journee du JJ-MM-AAAA caisse XX"
            libelle_transit = _generer_libelle_transit(date_transaction, num_caisse)

            virements_par_caisse[(date_compta, num_caisse)]["lignes"].append({
                "STE":        STE_DLM,
                "DATE":       date_compta,
                "COMPTE":     COMPTE_AMEX_CAISSE_TRANSIT,
                "Auxiliaire": "",
                "n°pièce":    n_piece,
                "OBJET":      libelle_transit,
                "D":          "",
                "C":          format_montant_compta(montant_brut),
                "Journal":    JOURNAL_CAA,
                "Analytique": "",
            })

            # Accumulation des frais par date (pour regroupement unique)
            if frais != 0.0:
                frais_par_date[date_compta] += abs(frais)

        # Accumulation pour ligne banque
        banque_par_date[date_compta] += montant_net

    # ----------------------------------------------------------
    # 6. Génération finale
    # ----------------------------------------------------------
    lignes_finales = []

    # ─────────────────────────────────────────────────────
    # AJOUT 1 : Toutes les lignes 580011 (par caisse)
    # ─────────────────────────────────────────────────────
    for (date_compta, num_caisse), data in sorted(virements_par_caisse.items()):
        lignes_finales.extend(data["lignes"])

    # ─────────────────────────────────────────────────────
    # AJOUT 2 : UNE SEULE ligne 627800 par date (regroupée)
    # ─────────────────────────────────────────────────────
    for date_compta in sorted(frais_par_date.keys()):
        total_frais = round(frais_par_date[date_compta], 2)

        if total_frais == 0.0:
            continue

        cle_date_frais = _date_en_cle(date_compta)
        n_piece_frais  = f"AMEX-{cle_date_frais}"
        libelle_frais  = _generer_libelle_frais(date_compta)

        lignes_finales.append({
            "STE":        STE_DLM,
            "DATE":       date_compta,
            "COMPTE":     COMPTE_FRAIS_CB,
            "Auxiliaire": "",
            "n°pièce":    n_piece_frais,
            "OBJET":      libelle_frais,
            "D":          format_montant_compta(total_frais),
            "C":          "",
            "Journal":    JOURNAL_CAA,
            "Analytique": ANALYTIQUE_FRAIS_CB,
        })

    # ─────────────────────────────────────────────────────
    # AJOUT 3 : Ligne banque 512121 (UNE PAR DATE)
    # ─────────────────────────────────────────────────────
    for date_compta in sorted(banque_par_date.keys()):
        total_net = round(banque_par_date[date_compta], 2)

        if total_net == 0.0:
            logger.warning(
                f"[AMEX_CAISSE] Total net nul pour {date_compta}, ligne banque ignorée"
            )
            continue

        cle_date_banque = _date_en_cle(date_compta)
        n_piece_banque  = f"AMEX-{cle_date_banque}"
        libelle_banque  = _generer_libelle_banque(date_compta)

        lignes_finales.append({
            "STE":        STE_DLM,
            "DATE":       date_compta,
            "COMPTE":     COMPTE_BANQUE_AMEX_CAISSE,
            "Auxiliaire": "",
            "n°pièce":    n_piece_banque,
            "OBJET":      libelle_banque,
            "D":          format_montant_compta(total_net),
            "C":          "",
            "Journal":    JOURNAL_CAA,
            "Analytique": "",
        })

    # ----------------------------------------------------------
    # 7. Export CSV
    # ----------------------------------------------------------
    if not lignes_finales:
        msg = f"Aucune écriture générée pour {fichier.name}"
        return "AUCUNE_DONNEE", msg

    try:
        DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

        df_final = pd.DataFrame(lignes_finales)
        sortie   = DOSSIER_SORTIE / f"{fichier.stem}_amex_caisse.csv"
        df_final.to_csv(
            sortie,
            sep=";",
            index=False,
            encoding="latin1",
            columns=COLONNES_SORTIE,
        )

        logger.info(f"[AMEX_CAISSE] ✅ {len(lignes_finales)} écritures générées")
        return "OK", str(sortie)

    except Exception as e:
        msg = f"Erreur export CSV : {e}"
        logger.error(f"[AMEX_CAISSE] ❌ {msg}", exc_info=True)
        return "ERREUR", msg


__all__ = ["traiter_amex_caisse"]
