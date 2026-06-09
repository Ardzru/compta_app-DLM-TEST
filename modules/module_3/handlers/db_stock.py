# modules/module_3/handlers/db_stock.py
"""
CRUD sur stock_especes, stock_cheques_vac, stock_cheques,
stock_ancv et mouvements_stock.
Remplace entièrement stock.json.
"""

import json
from datetime import date
from typing import Optional, Dict, List
from core.database import get_connection, get_cursor
from config import logger

# =============================================================================
# ESPÈCES
# =============================================================================

def lire_stock_especes() -> Dict[float, Dict]:
    """
    Retourne le stock espèces par dénomination.

    Returns:
        {500: {'quantite': 10, 'montant_total': 5000.0}, ...}
    """
    logger.debug("[DB_STOCK][ESP] lire_stock_especes")
    try:
        with get_cursor() as cur:
            cur.execute(
                "SELECT denomination, quantite, montant_total "
                "FROM stock_especes ORDER BY denomination DESC"
            )
            return {
                float(r["denomination"]): {
                    "quantite":     int(r["quantite"]),
                    "montant_total": float(r["montant_total"]),
                }
                for r in cur.fetchall()
            }
    except Exception as e:
        logger.error(f"[DB_STOCK][ESP] lire ECHEC : {e}")
        return {}


def lire_total_stock_especes() -> float:
    """Total € en espèces."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(montant_total), 0) FROM stock_especes")
            row = cur.fetchone()
            return float(list(row.values())[0]) if row else 0.0
    except Exception as e:
        logger.error(f"[DB_STOCK][ESP] lire_total ECHEC : {e}")
        return 0.0


def maj_stock_espece(
    denomination: float,
    quantite: int,
    montant_total: float,
    date_maj_caisse: date,
    source: str = "UI_MANUAL",
) -> bool:
    """
    Met à jour (UPSERT) une coupure dans stock_especes
    et enregistre le mouvement.
    """
    logger.info(
        f"[DB_STOCK][ESP] maj denom={denomination} "
        f"qte={quantite} montant={montant_total} source={source}"
    )
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # UPSERT stock
                cur.execute(
                    """
                    INSERT INTO stock_especes (denomination, quantite, montant_total, derniere_maj)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (denomination) DO UPDATE SET
                        quantite      = stock_especes.quantite + EXCLUDED.quantite,
                        montant_total = stock_especes.montant_total + EXCLUDED.montant_total,
                        derniere_maj  = now()
                    """,
                    (denomination, quantite, montant_total)
                )
                # Mouvement
                cur.execute(
                    """
                    INSERT INTO mouvements_stock
                        (article, type_mouvement, quantite, montant, source, date_maj_caisse)
                    VALUES (%s, 'ENTREE', %s, %s, %s, %s)
                    """,
                    (f"ESPECE_{denomination}", quantite, montant_total,
                     source, date_maj_caisse)
                )
                conn.commit()
                logger.info(f"[DB_STOCK][ESP] maj OK denom={denomination}")
                return True
    except Exception as e:
        logger.error(f"[DB_STOCK][ESP] maj ECHEC : {e}", exc_info=True)
        return False


def retirer_stock_espece(
    denomination: float,
    quantite: int,
    montant_total: float,
    source: str = "REMISE",
) -> bool:
    """Décrémente une coupure (lors d'une remise banque)."""
    logger.info(
        f"[DB_STOCK][ESP] retrait denom={denomination} "
        f"qte={quantite} source={source}"
    )
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE stock_especes SET
                        quantite      = GREATEST(0, quantite - %s),
                        montant_total = GREATEST(0, montant_total - %s),
                        derniere_maj  = now()
                    WHERE denomination = %s
                    """,
                    (quantite, montant_total, denomination)
                )
                cur.execute(
                    """
                    INSERT INTO mouvements_stock
                        (article, type_mouvement, quantite, montant, source)
                    VALUES (%s, 'SORTIE', %s, %s, %s)
                    """,
                    (f"ESPECE_{denomination}", quantite, montant_total, source)
                )
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"[DB_STOCK][ESP] retrait ECHEC : {e}", exc_info=True)
        return False


# =============================================================================
# CHÈQUES VACANCES
# =============================================================================

def lire_stock_cheques_vac() -> Dict[float, Dict]:
    """Retourne le stock chèques vacances par coupure."""
    logger.debug("[DB_STOCK][CVA] lire_stock_cheques_vac")
    try:
        with get_cursor() as cur:
            cur.execute(
                "SELECT denomination, quantite, montant_total "
                "FROM stock_cheques_vac ORDER BY denomination DESC"
            )
            return {
                float(r["denomination"]): {
                    "quantite":     int(r["quantite"]),
                    "montant_total": float(r["montant_total"]),
                }
                for r in cur.fetchall()
            }
    except Exception as e:
        logger.error(f"[DB_STOCK][CVA] lire ECHEC : {e}")
        return {}


def maj_stock_cheque_vac(
    denomination: float,
    quantite: int,
    source: str = "CAISSE",
) -> bool:
    """Ajoute des chèques vacances au stock."""
    montant = round(denomination * quantite, 2)
    logger.info(
        f"[DB_STOCK][CVA] maj denom={denomination} qte={quantite} "
        f"montant={montant} source={source}"
    )
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO stock_cheques_vac (denomination, quantite, montant_total)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (denomination) DO UPDATE SET
                        quantite      = stock_cheques_vac.quantite + EXCLUDED.quantite,
                        montant_total = stock_cheques_vac.montant_total + EXCLUDED.montant_total,
                        derniere_maj  = now()
                    """,
                    (denomination, quantite, montant)
                )
                cur.execute(
                    """
                    INSERT INTO mouvements_stock
                        (article, type_mouvement, quantite, montant, source)
                    VALUES (%s, 'ENTREE', %s, %s, %s)
                    """,
                    (f"CHEQUE_VAC_{denomination}", quantite, montant, source)
                )
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"[DB_STOCK][CVA] maj ECHEC : {e}", exc_info=True)
        return False


def retirer_stock_cheque_vac(denomination: float, quantite: int,
                              source: str = "REMISE") -> bool:
    """Décrémente des chèques vacances (remise)."""
    montant = round(denomination * quantite, 2)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE stock_cheques_vac SET
                        quantite      = GREATEST(0, quantite - %s),
                        montant_total = GREATEST(0, montant_total - %s),
                        derniere_maj  = now()
                    WHERE denomination = %s
                    """,
                    (quantite, montant, denomination)
                )
                cur.execute(
                    """
                    INSERT INTO mouvements_stock
                        (article, type_mouvement, quantite, montant, source)
                    VALUES (%s, 'SORTIE', %s, %s, %s)
                    """,
                    (f"CHEQUE_VAC_{denomination}", quantite, montant, source)
                )
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"[DB_STOCK][CVA] retrait ECHEC : {e}", exc_info=True)
        return False


# =============================================================================
# CHÈQUES BANCAIRES
# =============================================================================

def ajouter_cheques(cheques: List[Dict], caisse_ref: str,
                    date_caisse: date) -> bool:
    """
    Insère des chèques en stock.

    cheques = [{"numero": "123", "montant": 150.0}, ...]
    """
    if not cheques:
        return True
    logger.info(
        f"[DB_STOCK][CHQ] ajouter {len(cheques)} chèques "
        f"caisse={caisse_ref} date={date_caisse}"
    )
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for ch in cheques:
                    cur.execute(
                        """
                        INSERT INTO stock_cheques
                            (numero, montant, caisse_ref, date_caisse)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            str(ch.get("numero") or ch.get("num", "")),
                            float(ch.get("montant", 0)),
                            str(caisse_ref),
                            date_caisse,
                        )
                    )
                conn.commit()
                logger.info(f"[DB_STOCK][CHQ] {len(cheques)} chèque(s) insérés")
                return True
    except Exception as e:
        logger.error(f"[DB_STOCK][CHQ] ajouter ECHEC : {e}", exc_info=True)
        return False


def lire_cheques_en_stock() -> List[Dict]:
    """Retourne tous les chèques avec statut EN_STOCK."""
    try:
        with get_cursor() as cur:
            cur.execute(
                "SELECT * FROM stock_cheques WHERE statut = 'EN_STOCK' "
                "ORDER BY date_caisse, numero"
            )
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.error(f"[DB_STOCK][CHQ] lire ECHEC : {e}")
        return []


def marquer_cheques_remis(numeros: List[str], remise_id: int) -> bool:
    """Passe les chèques à statut REMIS."""
    if not numeros:
        return True
    logger.info(f"[DB_STOCK][CHQ] marquer_remis {len(numeros)} chèques remise_id={remise_id}")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE stock_cheques SET statut = 'REMIS', remise_id = %s
                    WHERE numero = ANY(%s)
                    """,
                    (remise_id, numeros)
                )
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"[DB_STOCK][CHQ] marquer_remis ECHEC : {e}", exc_info=True)
        return False


# =============================================================================
# ANCV
# =============================================================================

def ajouter_ancv(montant: float, caisse_ref: str, date_caisse: date) -> bool:
    """Ajoute un montant ANCV au stock."""
    logger.info(
        f"[DB_STOCK][ANCV] ajouter montant={montant} "
        f"caisse={caisse_ref} date={date_caisse}"
    )
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO stock_ancv (date_caisse, caisse_ref, montant)
                    VALUES (%s, %s, %s)
                    """,
                    (date_caisse, str(caisse_ref), montant)
                )
                cur.execute(
                    """
                    INSERT INTO mouvements_stock
                        (article, type_mouvement, quantite, montant, source, date_maj_caisse)
                    VALUES ('ANCV', 'ENTREE', 1, %s, %s, %s)
                    """,
                    (montant, f"CAISSE_{caisse_ref}", date_caisse)
                )
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"[DB_STOCK][ANCV] ajouter ECHEC : {e}", exc_info=True)
        return False


def lire_total_ancv_en_stock() -> float:
    """Total ANCV non remis."""
    try:
        with get_cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(montant), 0) FROM stock_ancv WHERE statut = 'EN_STOCK'"
            )
            row = cur.fetchone()
            return float(list(row.values())[0]) if row else 0.0
    except Exception as e:
        logger.error(f"[DB_STOCK][ANCV] lire_total ECHEC : {e}")
        return 0.0


# =============================================================================
# TOTAUX GÉNÉRAUX
# =============================================================================

def get_totaux_stock() -> Dict[str, float]:
    """
    Retourne un résumé complet du stock.

    Returns:
        {
            'especes': 1500.0,
            'cheques_vac': 300.0,
            'cheques': 450.0,
            'ancv': 120.0,
            'total': 2370.0,
        }
    """
    logger.debug("[DB_STOCK] get_totaux_stock")
    try:
        with get_cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(montant_total), 0) FROM stock_especes")
            esp = float(list(cur.fetchone().values())[0])

            cur.execute("SELECT COALESCE(SUM(montant_total), 0) FROM stock_cheques_vac")
            cva = float(list(cur.fetchone().values())[0])

            cur.execute(
                "SELECT COALESCE(SUM(montant), 0) FROM stock_cheques WHERE statut = 'EN_STOCK'"
            )
            chq = float(list(cur.fetchone().values())[0])

            cur.execute(
                "SELECT COALESCE(SUM(montant), 0) FROM stock_ancv WHERE statut = 'EN_STOCK'"
            )
            ancv = float(list(cur.fetchone().values())[0])

        total = round(esp + cva + chq + ancv, 2)
        result = {
            "especes":    round(esp, 2),
            "cheques_vac": round(cva, 2),
            "cheques":    round(chq, 2),
            "ancv":       round(ancv, 2),
            "total":      total,
        }
        logger.info(f"[DB_STOCK] totaux={result}")
        return result
    except Exception as e:
        logger.error(f"[DB_STOCK] get_totaux ECHEC : {e}")
        return {"especes": 0, "cheques_vac": 0, "cheques": 0, "ancv": 0, "total": 0}


# =============================================================================
# MOUVEMENTS
# =============================================================================

def lire_mouvements(
    article: Optional[str] = None,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    limite: int = 500,
) -> List[Dict]:
    """Récupère les mouvements avec filtres optionnels."""
    logger.debug(
        f"[DB_STOCK][MOV] lire article={article} "
        f"debut={date_debut} fin={date_fin}"
    )
    try:
        with get_cursor() as cur:
            sql = "SELECT * FROM mouvements_stock WHERE 1=1"
            params: list = []

            if article:
                sql += " AND article = %s"
                params.append(article)
            if date_debut:
                sql += " AND date_mouvement >= %s"
                params.append(date_debut)
            if date_fin:
                sql += " AND date_mouvement <= %s"
                params.append(date_fin)

            sql += " ORDER BY date_mouvement DESC LIMIT %s"
            params.append(limite)

            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.error(f"[DB_STOCK][MOV] lire ECHEC : {e}")
        return []


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Espèces
    "lire_stock_especes",
    "lire_total_stock_especes",
    "maj_stock_espece",
    "retirer_stock_espece",
    # Chèques vac
    "lire_stock_cheques_vac",
    "maj_stock_cheque_vac",
    "retirer_stock_cheque_vac",
    # Chèques
    "ajouter_cheques",
    "lire_cheques_en_stock",
    "marquer_cheques_remis",
    # ANCV
    "ajouter_ancv",
    "lire_total_ancv_en_stock",
    # Totaux
    "get_totaux_stock",
    # Mouvements
    "lire_mouvements",
]
