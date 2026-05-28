# handlers/module_1/traiter_alma.py

"""
Traitement des fichiers Alma Payments.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from config import DOSSIER_SORTIE, COLONNES_SORTIE
from logger import logger

# ============================================================================
# CONSTANTES COMPTABLES
# ============================================================================

STE        = "DLM"
JOURNAL    = "ALMA"
ANALYTIQUE = ""
COMPTE     = "580013DS5"  # À adapter selon ta structure
AUXILIAIRE = "ALMA PAYMENTS"

# ============================================================================
# MAPPING COLONNES ALMA
# ============================================================================

COL_ID_PAIEMENT     = "Identifiant paiement"
COL_DATE            = "Créé (Heure Europe/Paris)"
COL_MONTANT         = "Montant achat"
COL_ECHANCES        = "Nombre d'échéances"
COL_FRAIS           = "Frais marchand"
COL_REMBOURSEMENT   = "Montant remboursé"
COL_EMAIL           = "Email client"
COL_COMMANDE        = "Référence de commande"
COL_MARCHAND        = "Nom marchand"

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def formater_montant_alma(centimes: float) -> float:
    """Convertit les centimes en euros."""
    try:
        return round(float(centimes) / 100, 2)
    except (ValueError, TypeError):
        return 0.0

def formater_date_alma(date_str: str) -> str:
    """Formate la date au format JJ-MM-AAAA."""
    try:
        d = pd.to_datetime(date_str)
        return d.strftime("%d-%m-%Y")
    except Exception:
        return ""

# ============================================================================
# TRAITEMENT PRINCIPAL
# ============================================================================

def traiter_alma(fichier: Path) -> dict:
    """
    Traite un fichier de paiements Alma.

    Returns:
        dict avec clés: succes, erreurs, fichier_sortie, messages
    """
    logger.info(f"🔄 ALMA PAYMENTS : {fichier.name}")

    try:
        # ────────────────────────────────────────────────────────────────
        # 1. LECTURE
        # ────────────────────────────────────────────────────────────────
        df = pd.read_excel(fichier, engine="openpyxl")
        logger.info(f"   ✓ {len(df)} transactions lues")

        if df.empty:
            logger.warning(f"   ⚠️ Fichier vide")
            return {"succes": 0, "erreurs": 0}

        # ────────────────────────────────────────────────────────────────
        # 2. CONSTRUCTION SORTIE COMPTA
        # ────────────────────────────────────────────────────────────────
        lignes = []

        for idx, row in df.iterrows():
            try:
                # Récupérer les valeurs
                montant_centimes = row.get(COL_MONTANT, 0)
                montant_eur = formater_montant_alma(montant_centimes)

                date = formater_date_alma(str(row.get(COL_DATE, "")))
                commande = str(row.get(COL_COMMANDE, "")).strip()
                email = str(row.get(COL_EMAIL, "")).strip()

                if not montant_eur or montant_eur == 0:
                    logger.warning(f"   ⚠️ Ligne {idx+2}: montant vide, ignorée")
                    continue

                if not date:
                    logger.warning(f"   ⚠️ Ligne {idx+2}: date invalide, ignorée")
                    continue

                # Construire le libellé
                libelle_parts = ["ALMA"]
                if commande:
                    libelle_parts.append(f"Réf: {commande}")
                if email:
                    libelle_parts.append(email)

                libelle = " - ".join(libelle_parts)

                # Construire la ligne de sortie
                ligne = {
                    "STE": STE,
                    "DATE": date,
                    "COMPTE": COMPTE,
                    "Auxiliaire": AUXILIAIRE,
                    "n°pièce": commande if commande else f"ALMA_{idx+1}",
                    "OBJET": libelle[:200],  # Limiter la longueur
                    "D": f"{montant_eur:.2f}".replace(".", ","),  # Débit en format français
                    "C": "",  # Crédit vide
                    "Journal": JOURNAL,
                    "Analytique": ANALYTIQUE,
                }

                lignes.append(ligne)

            except Exception as e:
                logger.error(f"   ❌ Ligne {idx+2}: {e}")
                continue

        # ────────────────────────────────────────────────────────────────
        # 3. EXPORT CSV
        # ────────────────────────────────────────────────────────────────
        if not lignes:
            logger.warning(f"   ⚠️ Aucune ligne exploitable")
            return {"succes": 0, "erreurs": len(df)}

        df_sortie = pd.DataFrame(lignes)

        # Respecter l'ordre des colonnes
        df_sortie = df_sortie[COLONNES_SORTIE]

        # Générer le nom de fichier
        date_export = datetime.now().strftime("%Y%m%d_%H%M%S")
        nom_sortie = f"ALMA_{date_export}.csv"
        chemin_sortie = DOSSIER_SORTIE / nom_sortie

        # Écrire en CSV
        df_sortie.to_csv(
            chemin_sortie,
            sep=";",
            index=False,
            encoding="latin-1",
            quoting=1  # QUOTE_ALL
        )

        logger.info(f"✅ ALMA : {chemin_sortie.name} ({len(lignes)} écritures)")

        return {
            "succes": len(lignes),
            "erreurs": len(df) - len(lignes),
            "fichier_sortie": str(chemin_sortie)
        }

    except Exception as e:
        logger.error(f"❌ ALMA : {e}", exc_info=True)
        return {
            "succes": 0,
            "erreurs": 1,
            "erreur": str(e)
        }


__all__ = ["traiter_alma"]
