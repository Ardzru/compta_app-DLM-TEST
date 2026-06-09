"""
Wrapper PostgreSQL avec fallback JSON.
Utilisé par tous les handlers Module 3.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from config import logger, DB_CONFIG, BASE_DIR
from pathlib import Path
import json
from typing import Optional, List, Dict, Any

# ══════════════════════════════════════════════════════════════════════════════
# CLIENT POSTGRESQL AVEC FALLBACK JSON
# ══════════════════════════════════════════════════════════════════════════════

class PostgreSQLClient:
    """Client PostgreSQL avec fallback JSON."""

    def __init__(self):
        self.config = DB_CONFIG
        self.json_fallback_dir = BASE_DIR / "data" / "json_fallback"
        self.json_fallback_dir.mkdir(parents=True, exist_ok=True)
        self.is_available = self._test_connexion()
        logger.info(f"PostgreSQL available: {self.is_available}")

    def _test_connexion(self) -> bool:
        """Teste la connexion PostgreSQL."""
        try:
            conn = psycopg2.connect(**self.config)
            conn.close()
            logger.info("✅ PostgreSQL connecté")
            return True
        except Exception as exc:
            logger.warning(f"⚠️ PostgreSQL down, fallback JSON: {exc}")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # CAISSES
    # ─────────────────────────────────────────────────────────────────────────

    def inserer_caisse(self, date_caisse: str, num_caisse: str, donnees: dict) -> bool:
        """
        Insère une caisse en DB.

        Args:
            date_caisse: "2026-05-13"
            num_caisse: "60"
            donnees: dict complet des montants

        Returns:
            True si succès
        """
        if not self.is_available:
            return self._inserer_caisse_json(date_caisse, num_caisse, donnees)

        try:
            conn = psycopg2.connect(**self.config)
            cur = conn.cursor()

            sql = """
                INSERT INTO caisses 
                (date_caisse, num_caisse, especes_bande, cb_visa, amex, 
                 ancv_connect, cheques, donnees_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (date_caisse, num_caisse) 
                DO UPDATE SET donnees_json = EXCLUDED.donnees_json, updated_at = NOW()
            """

            especes = float(donnees.get("especes_bande", 0) or 0)
            cb_visa = float(donnees.get("cb_visa", 0) or 0)
            amex = float(donnees.get("amex", 0) or 0)
            ancv = float(donnees.get("ancv_connect", 0) or 0)
            cheques = float(donnees.get("cheques_bande", 0) or 0)

            cur.execute(sql, (
                date_caisse, num_caisse, especes, cb_visa, amex, ancv, cheques,
                json.dumps(donnees, ensure_ascii=False)
            ))

            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"✅ Caisse {num_caisse}/{date_caisse} insérée en DB")
            return True

        except Exception as exc:
            logger.error(f"❌ Erreur insertion caisse: {exc}")
            return self._inserer_caisse_json(date_caisse, num_caisse, donnees)

    def _inserer_caisse_json(self, date_caisse: str, num_caisse: str, donnees: dict) -> bool:
        """Fallback JSON pour caisses."""
        try:
            fichier = self.json_fallback_dir / f"caisses_{date_caisse}.json"
            data = []
            if fichier.exists():
                data = json.loads(fichier.read_text(encoding="utf-8"))
            data.append({
                "num_caisse": str(num_caisse),
                "donnees": donnees,
                "timestamp": str(json.encoder.JSONEncoder().default)
            })
            fichier.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"✅ Caisse {num_caisse} sauvegardée en JSON (fallback)")
            return True
        except Exception as exc:
            logger.error(f"❌ Erreur fallback JSON: {exc}")
            return False

    def charger_caisses(self, date_caisse: str) -> List[Dict[str, Any]]:
        """Charge les caisses d'une date depuis DB."""
        if not self.is_available:
            return self._charger_caisses_json(date_caisse)

        try:
            conn = psycopg2.connect(**self.config)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT * FROM caisses WHERE date_caisse = %s ORDER BY num_caisse",
                (date_caisse,)
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(row) for row in rows] if rows else []
        except Exception as exc:
            logger.warning(f"⚠️ Erreur lecture DB caisses: {exc}")
            return self._charger_caisses_json(date_caisse)

    def _charger_caisses_json(self, date_caisse: str) -> List[Dict[str, Any]]:
        """Fallback JSON pour charger caisses."""
        try:
            fichier = self.json_fallback_dir / f"caisses_{date_caisse}.json"
            if fichier.exists():
                return json.loads(fichier.read_text(encoding="utf-8"))
            return []
        except Exception as exc:
            logger.error(f"❌ Erreur fallback JSON lecture: {exc}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # REMISES
    # ─────────────────────────────────────────────────────────────────────────

    def inserer_remise(self, remise: dict) -> int:
        """
        Insère une remise.

        Args:
            remise: dict avec clés:
                - date_caisse, num_caisse, type, montant_total, detail, remis_banque

        Returns:
            ID de la remise, ou -1 si erreur
        """
        if not self.is_available:
            return self._inserer_remise_json(remise)

        try:
            conn = psycopg2.connect(**self.config)
            cur = conn.cursor()

            sql = """
                INSERT INTO remises 
                (date_caisse, num_caisse, type, montant_total, detail_json, 
                 remis_banque, valide_stock, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """

            cur.execute(sql, (
                remise.get("date_caisse"),
                remise.get("num_caisse"),
                remise.get("type"),
                remise.get("montant_total", 0.0),
                json.dumps(remise.get("detail", {}), ensure_ascii=False),
                remise.get("remis_banque", False),
                remise.get("valide_stock", False),
            ))

            remise_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"✅ Remise #{remise_id} insérée en DB")
            return remise_id

        except Exception as exc:
            logger.error(f"❌ Erreur insertion remise: {exc}")
            return self._inserer_remise_json(remise)

    def _inserer_remise_json(self, remise: dict) -> int:
        """Fallback JSON pour remises."""
        try:
            fichier = self.json_fallback_dir / "remises.json"
            data = []
            if fichier.exists():
                data = json.loads(fichier.read_text(encoding="utf-8"))
            remise_id = max([r.get("id", 0) for r in data], default=0) + 1
            remise["id"] = remise_id
            data.append(remise)
            fichier.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"✅ Remise #{remise_id} sauvegardée en JSON (fallback)")
            return remise_id
        except Exception as exc:
            logger.error(f"❌ Erreur fallback JSON remise: {exc}")
            return -1

    def charger_remises(self, date_caisse: str) -> List[Dict[str, Any]]:
        """Charge les remises d'une date."""
        if not self.is_available:
            return self._charger_remises_json(date_caisse)

        try:
            conn = psycopg2.connect(**self.config)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT * FROM remises WHERE date_caisse = %s ORDER BY id DESC",
                (date_caisse,)
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(row) for row in rows] if rows else []
        except Exception as exc:
            logger.warning(f"⚠️ Erreur lecture DB remises: {exc}")
            return self._charger_remises_json(date_caisse)

    def _charger_remises_json(self, date_caisse: str) -> List[Dict[str, Any]]:
        """Fallback JSON pour charger remises."""
        try:
            fichier = self.json_fallback_dir / "remises.json"
            if fichier.exists():
                data = json.loads(fichier.read_text(encoding="utf-8"))
                return [r for r in data if r.get("date_caisse") == date_caisse]
            return []
        except Exception as exc:
            logger.error(f"❌ Erreur fallback JSON remises: {exc}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # VÉRIFICATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def inserer_verification(self, date_caisse: str, donnees: dict) -> bool:
        """Insère une vérification."""
        if not self.is_available:
            return self._inserer_verification_json(date_caisse, donnees)

        try:
            conn = psycopg2.connect(**self.config)
            cur = conn.cursor()

            sql = """
                INSERT INTO verifications 
                (date_caisse, donnees_json, created_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (date_caisse) 
                DO UPDATE SET donnees_json = EXCLUDED.donnees_json, updated_at = NOW()
            """

            cur.execute(sql, (date_caisse, json.dumps(donnees, ensure_ascii=False)))
            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"✅ Vérification {date_caisse} insérée en DB")
            return True

        except Exception as exc:
            logger.error(f"❌ Erreur insertion vérification: {exc}")
            return self._inserer_verification_json(date_caisse, donnees)

    def _inserer_verification_json(self, date_caisse: str, donnees: dict) -> bool:
        """Fallback JSON pour vérifications."""
        try:
            fichier = self.json_fallback_dir / "verifications.json"
            data = {}
            if fichier.exists():
                data = json.loads(fichier.read_text(encoding="utf-8"))
            data[date_caisse] = donnees
            fichier.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"✅ Vérification {date_caisse} sauvegardée en JSON (fallback)")
            return True
        except Exception as exc:
            logger.error(f"❌ Erreur fallback JSON vérif: {exc}")
            return False

    def charger_verification(self, date_caisse: str) -> Optional[Dict[str, Any]]:
        """Charge une vérification."""
        if not self.is_available:
            return self._charger_verification_json(date_caisse)

        try:
            conn = psycopg2.connect(**self.config)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT donnees_json FROM verifications WHERE date_caisse = %s", (date_caisse,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return json.loads(row["donnees_json"])
            return None
        except Exception as exc:
            logger.warning(f"⚠️ Erreur lecture DB vérif: {exc}")
            return self._charger_verification_json(date_caisse)

    def _charger_verification_json(self, date_caisse: str) -> Optional[Dict[str, Any]]:
        """Fallback JSON pour charger vérification."""
        try:
            fichier = self.json_fallback_dir / "verifications.json"
            if fichier.exists():
                data = json.loads(fichier.read_text(encoding="utf-8"))
                return data.get(date_caisse)
            return None
        except Exception as exc:
            logger.error(f"❌ Erreur fallback JSON vérif lecture: {exc}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

_db_client = None

def get_db_client() -> PostgreSQLClient:
    """Retourne l'instance unique du client DB."""
    global _db_client
    if _db_client is None:
        _db_client = PostgreSQLClient()
    return _db_client

__all__ = ["PostgreSQLClient", "get_db_client"]
