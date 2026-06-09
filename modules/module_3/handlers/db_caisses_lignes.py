# modules/module_3/handlers/db_caisses_lignes.py
"""
Opérations CRUD sur caisses_lignes.
Gestion des articles/lignes de chaque caisse.
"""

from datetime import date
from typing import Optional, Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG
from config import logger


def _get_conn():
    """Retourne une connexion PostgreSQL."""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        logger.error(f"[DB_CAISSES_LIGNES] Erreur connexion : {e}")
        raise


# ════════════════════════════════════════════════════════════════════════════════
# CRÉER
# ════════════════════════════════════════════════════════════════════════════════

def creer_lignes(
    caisse_id: int,
    date_caisse: date,
    lignes: List[Dict]
) -> bool:
    """
    Insère les lignes d'une caisse.

    Args:
        caisse_id: FK caisses_validees
        date_caisse: Date
        lignes: [
            {
                'num_ligne': 1,
                'article': 'Article 1',
                'quantite': 5,
                'prix_unitaire': 10.50,
                'montant_total': 52.50,
                'remise_percent': 0
            },
            ...
        ]

    Returns:
        True si succès
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            for ligne in (lignes or []):
                sql = """
                    INSERT INTO caisses_lignes 
                        (caisse_id, num_ligne, article, quantite, prix_unitaire, montant_total, remise_percent, date_caisse)
                    VALUES 
                        (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cur.execute(sql, (
                    caisse_id,
                    ligne.get('num_ligne'),
                    ligne.get('article'),
                    ligne.get('quantite'),
                    ligne.get('prix_unitaire'),
                    ligne.get('montant_total'),
                    ligne.get('remise_percent', 0),
                    date_caisse
                ))

            conn.commit()
            logger.info(f"[DB_CAISSES_LIGNES] {len(lignes)} lignes créées : caisse_id={caisse_id}")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB_CAISSES_LIGNES] Erreur création : {e}")
        return False
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════════
# LIRE
# ════════════════════════════════════════════════════════════════════════════════

def lire_lignes_caisse(caisse_id: int) -> List[Dict]:
    """
    Récupère toutes les lignes d'une caisse.

    Args:
        caisse_id: ID de la caisse

    Returns:
        Liste de dicts
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT * FROM caisses_lignes WHERE caisse_id = %s ORDER BY num_ligne"
            cur.execute(sql, (caisse_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def lire_ligne(ligne_id: int) -> Optional[Dict]:
    """
    Récupère une ligne spécifique.

    Args:
        ligne_id: ID

    Returns:
        Dict ou None
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT * FROM caisses_lignes WHERE id = %s"
            cur.execute(sql, (ligne_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def lire_total_lignes(caisse_id: int) -> float:
    """
    Récupère le total des lignes d'une caisse.

    Args:
        caisse_id: ID de la caisse

    Returns:
        Montant en €
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            sql = "SELECT COALESCE(SUM(montant_total), 0) FROM caisses_lignes WHERE caisse_id = %s"
            cur.execute(sql, (caisse_id,))
            result = cur.fetchone()
            return float(result[0]) if result else 0.0
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════════
# METTRE À JOUR
# ════════════════════════════════════════════════════════════════════════════════

def maj_ligne(
    ligne_id: int,
    quantite: Optional[int] = None,
    prix_unitaire: Optional[float] = None,
    remise_percent: Optional[float] = None
) -> bool:
    """
    Modifie une ligne (et recalcule montant_total).

    Args:
        ligne_id: ID
        quantite: Optionnel
        prix_unitaire: Optionnel
        remise_percent: Optionnel

    Returns:
        True si succès
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Récupérer les données actuelles
            sql = "SELECT quantite, prix_unitaire, remise_percent FROM caisses_lignes WHERE id = %s"
            cur.execute(sql, (ligne_id,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"[DB_CAISSES_LIGNES] Ligne introuvable : {ligne_id}")
                return False

            qte = quantite if quantite is not None else row[0]
            prix = prix_unitaire if prix_unitaire is not None else row[1]
            remise = remise_percent if remise_percent is not None else row[2]

            # Recalculer montant_total
            montant_brut = qte * prix
            montant_total = montant_brut * (1 - remise / 100)

            sql = """
                UPDATE caisses_lignes 
                SET quantite = %s, prix_unitaire = %s, remise_percent = %s, montant_total = %s
                WHERE id = %s
            """
            cur.execute(sql, (qte, prix, remise, montant_total, ligne_id))
            conn.commit()
            logger.debug(f"[DB_CAISSES_LIGNES] Ligne maj : ID={ligne_id}")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB_CAISSES_LIGNES] Erreur maj : {e}")
        return False
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════════
# SUPPRIMER
# ════════════════════════════════════════════════════════════════════════════════

def supprimer_ligne(ligne_id: int) -> bool:
    """
    Supprime une ligne.

    Args:
        ligne_id: ID

    Returns:
        True si succès
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            sql = "DELETE FROM caisses_lignes WHERE id = %s"
            cur.execute(sql, (ligne_id,))
            conn.commit()
            logger.info(f"[DB_CAISSES_LIGNES] Ligne supprimée : ID={ligne_id}")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB_CAISSES_LIGNES] Erreur suppression : {e}")
        return False
    finally:
        conn.close()


def supprimer_lignes_caisse(caisse_id: int) -> bool:
    """
    Supprime toutes les lignes d'une caisse.

    Args:
        caisse_id: ID de la caisse

    Returns:
        True si succès
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            sql = "DELETE FROM caisses_lignes WHERE caisse_id = %s"
            cur.execute(sql, (caisse_id,))
            conn.commit()
            logger.info(f"[DB_CAISSES_LIGNES] Lignes supprimées : caisse_id={caisse_id}")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB_CAISSES_LIGNES] Erreur suppression : {e}")
        return False
    finally:
        conn.close()
