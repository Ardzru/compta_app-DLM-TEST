import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Dict, Optional
from config import DOSSIER_SORTIE, FICHIER_CORRESPONDANCE_AMEX
from logger import logger
from core.moniteur_schema import comparer_schema

# ==========================================================
# INDEX DES COLONNES
# ==========================================================
# Colonnes des lignes SOC
COL_DATE_REGLEMENT   = 1   # Date de règlement      (ex: 02/02/2026)
COL_DATE_TRANSACTION = 14  # Date de transaction    (ex: 29/01/2026)  ← corrigé (était 12)
COL_TYPE             = 4   # Type                   (SOC/ROC)
COL_NUM_REF          = 3   # Numéro de référence    (ex: 20853)
COL_NUM_REGLEMENT    = 2   # Numéro de règlement    (ex: 4903025623)
COL_MONTANT_BRUT     = 20  # Total des opérations   (ex: 1.235,50)
COL_FRAIS            = 23  # Montant de la remise   (ex: 12,36-)
COL_MONTANT_NET      = 26  # Montant du règlement   (ex: 1.223,14)

# Colonnes des lignes ROC
COL_ROC_ID_TERMINAL  = 7   # ID Terminal AMEX       (ex: SCA85E05)  ← corrigé (était 8)

# ==========================================================
# UTILITAIRES
# ==========================================================

def nettoyer_montant(val) -> float:
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
        logger.warning(f"Montant invalide ignoré : {val!r}")
        return 0.0


def formater_date(val) -> Optional[str]:
    """Formate une date au format JJ-MM-AAAA."""
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        logger.warning(f"Date invalide ignorée : {val!r}")
        return None
    return d.strftime("%d-%m-%Y")

def date_en_cle(val) -> Optional[str]:
    """Retourne la date au format AAAAMMJJ pour le n° pièce."""
    d = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(d):
        return None
    return d.strftime("%Y%m%d")


def monter_montant(valeur: float) -> str:
    """Formate un float en chaîne comptable (virgule, 2 décimales)."""
    return f"{abs(valeur):.2f}".replace(".", ",")


# ==========================================================
# CORRESPONDANCE TERMINAUX
# ==========================================================

def charger_correspondance_amex(fichier_correspondance: Path) -> Dict[str, Dict[str, str]]:
    """Charge le fichier de correspondance ID Terminal → N° de caisse.

    Colonnes attendues dans le fichier CSV :
      - 'id_terminal'
      - 'numero_caisse'
      - 'compte_comptable'
    """
    if not fichier_correspondance.exists():
        raise FileNotFoundError(
            f"Fichier de correspondance AMEX introuvable : {fichier_correspondance}"
        )

    try:
        df = pd.read_csv(
            fichier_correspondance,
            sep=",",
            encoding="utf-8",
            dtype=str
        )
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

        logger.info(f"Correspondance AMEX chargée : {len(correspondance)} terminaux")
        return correspondance

    except KeyError as e:
        logger.error(f"Colonne manquante dans le fichier de correspondance : {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur chargement correspondance AMEX : {e}")
        raise

# ==========================================================
# CONSTRUCTION DU LIEN SOC → ID TERMINAL (via ROC enfants)
# ==========================================================

def construire_map_soc_terminal(df: pd.DataFrame) -> Dict[str, str]:
    """
    Parcourt le DataFrame et associe chaque SOC (par son index)
    à l'ID Terminal du premier ROC enfant trouvé.

    Retourne : { index_soc (int) : id_terminal (str) }
    """
    map_soc_terminal = {}
    current_soc_idx = None

    for idx, row in df.iterrows():
        type_ligne = str(row[COL_TYPE]).strip().upper()

        if type_ligne == "SOC":
            current_soc_idx = idx

        elif type_ligne == "ROC" and current_soc_idx is not None:
            # On prend le premier ROC rencontré pour cet SOC
            if current_soc_idx not in map_soc_terminal:
                id_terminal = str(row[COL_ROC_ID_TERMINAL]).strip()
                if id_terminal and id_terminal.lower() != "nan":
                    map_soc_terminal[current_soc_idx] = id_terminal

    return map_soc_terminal

# ==========================================================

# LIBELLÉ
# ==========================================================

def generer_libelle(date_transaction: str, num_caisse: str) -> str:
    """Génère le libellé : 'JOURNEE DU JJ-MM-AAAA CAISSE XX'"""
    return f"JOURNEE DU {date_transaction} CAISSE {num_caisse}"


# ==========================================================
# HANDLER PRINCIPAL
# ==========================================================

def traiter_amex_caisse(fichier: Path) -> None:
    """
    Traite un fichier AMEX caisse (.xlsx) et génère les écritures comptables.

    Structure des écritures par SOC :
      - 580011  C  montant brut     (virement interne)
      - 627800  D  frais AMEX       (si applicable)
    Puis UNE ligne par date de règlement ET par caisse :
      - 512121  D  total net        (ligne banque regroupée par caisse)
    """

    fichier = Path(fichier)
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier AMEX caisse introuvable : {fichier}")

    logger.info(f"Traitement AMEX CAISSE : {fichier.name}")

    # ----------------------------------------------------------
    # 1. Lecture du fichier
    # ----------------------------------------------------------
    try:
        df = pd.read_excel(fichier, header=None, engine="openpyxl")
    except Exception as e:
        logger.error(f"Impossible de lire {fichier.name} : {e}")
        raise

    # ----------------------------------------------------------
    # 1b. Vérification du schéma
    # ----------------------------------------------------------
    comparer_schema(df, "amex_caisse")

    # ----------------------------------------------------------
    # 2. Chargement de la correspondance terminaux
    # ----------------------------------------------------------
    correspondance = charger_correspondance_amex(FICHIER_CORRESPONDANCE_AMEX)

    # ----------------------------------------------------------
    # 3. Construction du lien SOC → ID Terminal via les ROC
    # ----------------------------------------------------------
    map_soc_terminal = construire_map_soc_terminal(df)

    # ----------------------------------------------------------
    # 4. Accumulation par date de règlement + caisse
    # Structure : { (date_compta, num_caisse): { "lignes": [...], "total_net": float } }
    # ----------------------------------------------------------
    groupes: dict = defaultdict(lambda: {"lignes": [], "total_net": 0.0})

    for idx, row in df.iterrows():

        # Filtrer uniquement les SOC
        if str(row[COL_TYPE]).strip().upper() != "SOC":
            continue

        # Dates
        date_compta = formater_date(row[COL_DATE_REGLEMENT])
        date_transaction = formater_date(row[COL_DATE_TRANSACTION])
        if not date_compta or not date_transaction:
            logger.warning(f"Ligne {idx} ignorée : date invalide")
            continue

        # Montants
        montant_brut = nettoyer_montant(row[COL_MONTANT_BRUT])
        frais        = nettoyer_montant(row[COL_FRAIS])
        montant_net  = nettoyer_montant(row[COL_MONTANT_NET])

        # ID Terminal → caisse via la map SOC→ROC
        id_terminal = map_soc_terminal.get(idx, "")
        info_caisse = correspondance.get(id_terminal, {})
        num_caisse  = info_caisse.get("caisse", "INCONNUE")

        if num_caisse == "INCONNUE":
            logger.warning(
                f"Ligne {idx} : ID Terminal inconnu '{id_terminal}' "
                f"→ caisse vide (à compléter dans la correspondance)"
            )

        # Libellé et pièce
        libelle   = generer_libelle(date_transaction, num_caisse)
        cle_date  = date_en_cle(row[COL_DATE_REGLEMENT])
        n_piece   = f"AMEX-{cle_date}"

        # ✅ Clé de regroupement = date + caisse
        cle_groupe = (date_compta, num_caisse)
        groupe = groupes[cle_groupe]

        if montant_brut < 0:
            # ------------------------------------------------------
            # Remboursement
            # ------------------------------------------------------
            groupe["lignes"].append({
                "STE"       : "DLM",
                "DATE"      : date_compta,
                "COMPTE"    : "411000",
                "Auxiliaire": "",
                "n°pièce"   : n_piece,
                "OBJET"     : libelle,
                "D"         : monter_montant(montant_brut),
                "C"         : "",
                "Journal"   : "CAA",
                "Analytique": "",
            })
            groupe["total_net"] += montant_net

        else:
            # ------------------------------------------------------
            # Encaissement
            # ------------------------------------------------------

            # Ligne 1 : virement interne (montant brut → 580011)
            groupe["lignes"].append({
                "STE"       : "DLM",
                "DATE"      : date_compta,
                "COMPTE"    : "580011",
                "Auxiliaire": "",
                "n°pièce"   : n_piece,
                "OBJET"     : libelle,
                "D"         : "",
                "C"         : monter_montant(montant_brut),
                "Journal"   : "CAA",
                "Analytique": "",
            })

            # Ligne 2 : frais AMEX (627800)
            if frais != 0.0:
                groupe["lignes"].append({
                    "STE"       : "DLM",
                    "DATE"      : date_compta,
                    "COMPTE"    : "627800",
                    "Auxiliaire": "",
                    "n°pièce"   : n_piece,
                    "OBJET"     : f"FRAIS AMEX - {libelle}",
                    "D"         : monter_montant(abs(frais)),
                    "C"         : "",
                    "Journal"   : "CAA",
                    "Analytique": "ST-CT00-XX",
                })

            groupe["total_net"] += montant_net

    # ----------------------------------------------------------
    # 5. Génération finale
    # ----------------------------------------------------------
    lignes_finales = []

    # Regroupement par date uniquement pour la ligne banque
    par_date: dict = defaultdict(lambda: {"lignes": [], "total_net": 0.0})

    for (date_compta, num_caisse), groupe in sorted(groupes.items()):
        par_date[date_compta]["lignes"].extend(groupe["lignes"])
        par_date[date_compta]["total_net"] += groupe["total_net"]

    for date_compta, data in sorted(par_date.items()):

        lignes_finales.extend(data["lignes"])

        total_net = round(data["total_net"], 2)

        if total_net == 0.0:
            logger.warning(
                f"Total net nul pour la date {date_compta}, ligne banque ignorée"
            )
            continue

        cle_date_banque = date_compta[6:] + date_compta[3:5] + date_compta[:2]
        n_piece_banque = f"AMEX-{cle_date_banque}"

        lignes_finales.append({
            "STE": "DLM",
            "DATE": date_compta,
            "COMPTE": "512121",
            "Auxiliaire": "",
            "n°pièce": n_piece_banque,
            "OBJET": data["lignes"][0]["OBJET"],
            "D": monter_montant(total_net),
            "C": "",
            "Journal": "CAA",
            "Analytique": "",
        })

    # ----------------------------------------------------------
    # 6. Export CSV
    # ----------------------------------------------------------
    if not lignes_finales:
        logger.warning(f"Aucune écriture générée pour {fichier.name}")
        return

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    df_final = pd.DataFrame(lignes_finales)
    sortie   = DOSSIER_SORTIE / f"{fichier.stem}_amex_caisse.csv"
    df_final.to_csv(sortie, sep=";", index=False, encoding="latin1")

    logger.info(
        f"Export AMEX CAISSE : {sortie.name} "
        f"({len(lignes_finales)} écritures)"
    )

