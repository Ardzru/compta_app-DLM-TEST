# core/database.py
"""
Connexion PostgreSQL centralisée.
Toute la couche DB passe par get_connection().
RÈGLE : core/ n'importe jamais modules/
"""

from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG
from config import logger

# =============================================================================
# CONNEXION
# =============================================================================

@contextmanager
def get_connection() -> Generator:
    """
    Context manager — connexion PostgreSQL.

    Usage :
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(...)
                conn.commit()
    """
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.debug("[DB] Connexion ouverte")
        yield conn
    except psycopg2.Error as e:
        logger.error(f"[DB] Erreur connexion : {e}")
        raise
    finally:
        if conn:
            conn.close()
            logger.debug("[DB] Connexion fermée")


@contextmanager
def get_cursor(commit: bool = False):
    """
    Context manager — curseur RealDict avec commit optionnel.

    Usage :
        with get_cursor(commit=True) as cur:
            cur.execute("INSERT ...")
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                yield cur
                if commit:
                    conn.commit()
                    logger.debug("[DB] Commit OK")
            except Exception as e:
                conn.rollback()
                logger.error(f"[DB] Rollback : {e}")
                raise


# =============================================================================
# UTILITAIRES
# =============================================================================

def test_connexion() -> bool:
    """Vérifie que la connexion DB fonctionne."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1")
        logger.info("[DB] Test connexion OK")
        return True
    except Exception as e:
        logger.error(f"[DB] Test connexion ÉCHEC : {e}")
        return False
