# modules/module_3/handlers/db_caisses_especes.py
"""
Opérations CRUD sur caisses_especes.
Gestion des montants en espèces par caisse.
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
        logger.error(f"[DB_CAISSES_ESPECES] Erreur connexion : {e}")
        raise


# ════════════════════════════════════════════════════════════════════════════════
# CRÉER
# ════════════════════════════════════════════════════════════════════════════════

def creer_especes(
    caisse_id: int,
    date_caisse: date,
    billets: Dict[int, int],
    pieces: Dict[int, int]
) -> bool:
    """
    Insère les montants d'espèces pour une caisse.

    Args:
        caisse_id: FK caisses_validees
        date_caisse: Date
        billets: {500: 2, 200: 1, 100: 5, ...}
        pieces: {2: 10, 1: 15, ...}

    Returns:
        True si succès
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Billets
            for denomination, quantite in (billets or {}).items():
                montant = (denomination * quantite) / 100.0
                sql = """
                    INSERT INTO caisses_especes 
                        (caisse_id, type, denomination, quantite, montant_total, date_caisse)
                    VALUES 
                        (%s, 'BILLET', %s, %s, %s, %s)
                """
                cur.execute(sql, (caisse_id, denomination, quantite, montant, date_caisse))

            # Pièces
            for denomination, quantite in (pieces or {}).items():
                montant = (denomination * quantite) / 100.0
                sql = """
                    INSERT INTO caisses_especes 
                        (caisse_id, type, denomination, quantite, montant_total, date_caisse)
                    VALUES 
                        (%s, 'PIECE', %s, %s, %s, %s)
                """
                cur.execute(sql, (caisse_id, denomination, quantite, montant, date_caisse))

            conn.commit()
            logger.info(f"[DB_CAISSES_ESPECES] Espèces créées : caisse_id={caisse_id}")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB_CAISSES_ESPECES] Erreur création : {e}")
        return False
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════════
# LIRE
# ════════════════════════════════════════════════════════════════════════════════

def lire_especes_caisse(caisse_id: int) -> List[Dict]:
    """
    Récupère tous les montants d'espèces d'une caisse.

    Args:
        caisse_id: ID de la caisse

    Returns:
        Liste de dicts
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT * FROM caisses_especes WHERE caisse_id = %s ORDER BY type, denomination DESC"
            cur.execute(sql, (caisse_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def lire_total_especes_caisse(caisse_id: int) -> float:
    """
    Récupère le total des espèces d'une caisse.

    Args:
        caisse_id: ID de la caisse

    Returns:
        Montant en €
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            sql = "SELECT COALESCE(SUM(montant_total), 0) FROM caisses_especes WHERE caisse_id = %s"
            cur.execute(sql, (caisse_id,))
            result = cur.fetchone()
            return float(result[0]) if result else 0.0
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════════
# METTRE À JOUR
# ════════════════════════════════════════════════════════════════════════════════

def maj_quantite_espece(espece_id: int, nouvelle_quantite: int) -> bool:
    """
    Modifie la quantité d'une dénomination.

    Args:
        espece_id: ID de la ligne espèce
        nouvelle_quantite: Nouvelle quantité

    Returns:
        True si succès
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Récupérer la dénomination pour recalculer montant
            sql = "SELECT denomination FROM caisses_especes WHERE id = %s"
            cur.execute(sql, (espece_id,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"[DB_CAISSES_ESPECES] Espèce introuvable : {espece_id}")
                return False

            denomination = row[0]
            nouveau_montant = (denomination * nouvelle_quantite) / 100.0

            sql = """
                UPDATE caisses_especes 
                SET quantite = %s, montant_total = %s
                WHERE id = %s
            """
            cur.execute(sql, (nouvelle_quantite, nouveau_montant, espece_id))
            conn.commit()
            logger.debug(f"[DB_CAISSES_ESPECES] Espèce maj : ID={espece_id}")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB_CAISSES_ESPECES] Erreur maj : {e}")
        return False
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════════
# SUPPRIMER
# ════════════════════════════════════════════════════════════════════════════════

def supprimer_especes_caisse(caisse_id: int) -> bool:
    """
    Supprime toutes les espèces d'une caisse.

    Args:
        caisse_id: ID de la caisse

    Returns:
        True si succès
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            sql = "DELETE FROM caisses_especes WHERE caisse_id = %s"
            cur.execute(sql, (caisse_id,))
            conn.commit()
            logger.info(f"[DB_CAISSES_ESPECES] Espèces supprimées : caisse_id={caisse_id}")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB_CAISSES_ESPECES] Erreur suppression : {e}")
        return False
    finally:
        conn.close()
