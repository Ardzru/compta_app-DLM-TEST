# modules/module_3/handlers/db_remises.py
"""
CRUD sur remises_banque.
"""

import json
from datetime import date
from typing import Optional, List, Dict
from core.database import get_connection, get_cursor
from config import logger

TYPES_VALIDES  = {"ESPECES", "CHEQUES_VAC", "CHEQUES", "ANCV"}
STATUTS_VALIDES = {"EN_COURS", "VALIDEE", "ANNULEE"}

# =============================================================================
# CRÉER
# =============================================================================

def creer_remise(
    type_remise: str,
    montant_total: float,
    detail: dict,
    date_remise: Optional[date] = None,
    reference_banque: Optional[str] = None,
    commentaire: Optional[str] = None,
) -> Optional[int]:
    """
    Crée une remise banque. Retourne l'ID ou None.

    detail = dict libre (billets, chèques, total...)
    """
    type_remise = type_remise.upper()
    if type_remise not in TYPES_VALIDES:
        logger.error(
            f"[DB_REMISES][CREER] Type invalide : {type_remise}. "
            f"Valides : {TYPES_VALIDES}"
        )
        return None

    logger.info(
        f"[DB_REMISES][CREER] type={type_remise} "
        f"montant={montant_total} date={date_remise}"
    )
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO remises_banque
                        (type_remise, montant_total, detail, date_remise,
                         reference_banque, commentaire)
                    VALUES (%s, %s, %s::jsonb, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        type_remise,
                        montant_total,
                        json.dumps(detail),
                        date_remise or date.today(),
                        reference_banque,
                        commentaire,
                    )
                )
                row = cur.fetchone()
                conn.commit()
                remise_id = row[0] if row else None
                logger.info(f"[DB_REMISES][CREER] OK id={remise_id}")
                return remise_id
    except Exception as e:
        logger.error(f"[DB_REMISES][CREER] ECHEC : {e}", exc_info=True)
        return None


# =============================================================================
# LIRE
# =============================================================================

def lire_remise(remise_id: int) -> Optional[Dict]:
    """Récupère une remise par ID."""
    try:
        with get_cursor() as cur:
            cur.execute(
                "SELECT * FROM remises_banque WHERE id = %s",
                (remise_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"[DB_REMISES][LIRE] ECHEC id={remise_id} : {e}")
        return None


def lire_remises(
    type_remise: Optional[str] = None,
    statut: Optional[str] = None,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    limite: int = 200,
) -> List[Dict]:
    """Récupère les remises avec filtres optionnels."""
    logger.debug(
        f"[DB_REMISES][LIRE] type={type_remise} statut={statut} "
        f"debut={date_debut} fin={date_fin}"
    )
    try:
        with get_cursor() as cur:
            sql = "SELECT * FROM remises_banque WHERE 1=1"
            params: list = []

            if type_remise:
                sql += " AND type_remise = %s"
                params.append(type_remise.upper())
            if statut:
                sql += " AND statut = %s"
                params.append(statut.upper())
            if date_debut:
                sql += " AND date_remise >= %s"
                params.append(date_debut)
            if date_fin:
                sql += " AND date_remise <= %s"
                params.append(date_fin)

            sql += " ORDER BY date_remise DESC LIMIT %s"
            params.append(limite)

            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.error(f"[DB_REMISES][LIRE] ECHEC : {e}")
        return []


# =============================================================================
# METTRE À JOUR
# =============================================================================

def valider_remise(remise_id: int,
                   reference_banque: Optional[str] = None) -> bool:
    """Passe la remise en VALIDEE."""
    logger.info(
        f"[DB_REMISES][VALIDER] id={remise_id} ref={reference_banque}"
    )
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE remises_banque SET
                        statut           = 'VALIDEE',
                        reference_banque = COALESCE(%s, reference_banque),
                        date_validation  = now()
                    WHERE id = %s
                    """,
                    (reference_banque, remise_id)
                )
                conn.commit()
                logger.info(f"[DB_REMISES][VALIDER] OK id={remise_id}")
                return True
    except Exception as e:
        logger.error(f"[DB_REMISES][VALIDER] ECHEC : {e}", exc_info=True)
        return False


def annuler_remise(remise_id: int, commentaire: Optional[str] = None) -> bool:
    """Annule une remise."""
    logger.warning(f"[DB_REMISES][ANNULER] id={remise_id}")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE remises_banque SET
                        statut      = 'ANNULEE',
                        commentaire = COALESCE(%s, commentaire)
                    WHERE id = %s
                    """,
                    (commentaire, remise_id)
                )
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"[DB_REMISES][ANNULER] ECHEC : {e}", exc_info=True)
        return False


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "creer_remise",
    "lire_remise",
    "lire_remises",
    "valider_remise",
    "annuler_remise",
    "TYPES_VALIDES",
    "STATUTS_VALIDES",
]
