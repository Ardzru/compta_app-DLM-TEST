import os
import threading
import pandas as pd
from openpyxl import Workbook
from pathlib import Path
from openpyxl.styles import PatternFill, Font

from config import logger
from core.utils.montant import to_float
from core.utils.colonnes import (
    COLONNES_COMPTA, COLONNES_BANQUE, COLONNES_ALPILINK, RE_COMMANDE
)

# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES PRIVÉS
# ══════════════════════════════════════════════════════════════════════════════

def _normaliser_cmd(val):
    """Normalise un numéro de commande."""
    if val is None:
        return None
    try:
        s = str(val).strip().split('.')[0].upper()
        return s if RE_COMMANDE.match(s) else None
    except Exception as e:
        logger.error(f"Normalisation échouée pour '{val}': {e}")
        return None


def _get_alpi_key(row):
    """Extrait la clé commande d'une ligne ALPILINK."""
    return _normaliser_cmd(row.get(COLONNES_ALPILINK["id_cmd"]))

# ══════════════════════════════════════════════════════════════════════════════
# HANDLER JUSTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class JustificationHandler:
    """
    Handler de justification des commandes.
    Rapproche COMPTA / BANQUE / ALPILINK.
    """

    def __init__(self, callback_log=None, callback_fin=None, callback_progression=None):
        self.lock = threading.Lock()
        self.log_messages = []
        self.callback_log = callback_log
        self.callback_fin = callback_fin
        self.callback_progression = callback_progression  # (valeur, texte)

    def log(self, message):
        """Log un message."""
        logger.info(message)
        with self.lock:
            self.log_messages.append(message)
        if self.callback_log:
            self.callback_log(message)

    def _progression(self, valeur, texte):
        """Met à jour la progression."""
        if self.callback_progression:
            self.callback_progression(valeur, texte)

    def lancer(self, fichiers, dossier_sortie):
        """Lance le traitement en thread."""
        if not fichiers:
            self.log("❌ Aucun fichier trouvé — abandon")
            if self.callback_fin:
                self.callback_fin([], [], [], [], [])
            return
        t = threading.Thread(
            target=self._run,
            args=(fichiers, dossier_sortie),
            daemon=True
        )
        t.start()

    def _lire_fichier(self, chemin):
        """Lit un fichier (CSV, XLS, XLSX)."""
        try:
            ext = Path(chemin).suffix.lower()
            if ext in ('.xlsx', '.xls'):
                df = pd.read_excel(chemin, dtype=str)
            elif ext == '.csv':
                df = pd.read_csv(chemin, dtype=str, sep=None, engine='python')
            else:
                logger.warning(f"Extension non supportée: {ext}")
                return None
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            logger.error(f"Erreur lecture {chemin}: {e}")
            return None

    def _detecter_type(self, df):
        """Détecte le type de fichier (compta/banque/alpilink)."""
        cols = set(df.columns.str.strip().str.lower())

        compta_cols  = {COLONNES_COMPTA["montant"].lower(),
                        COLONNES_COMPTA["journal"].lower()}
        banque_cols  = {COLONNES_BANQUE["date"].lower(),
                        COLONNES_BANQUE["commande"].lower()}
        alpi_cols    = {COLONNES_ALPILINK["id_cmd"].lower(),
                        COLONNES_ALPILINK["montant"].lower()}

        if compta_cols.issubset(cols):
            return "compta"
        if banque_cols.issubset(cols):
            return "banque"
        if alpi_cols.issubset(cols):
            return "alpilink"
        return "inconnu"

    def _extraire_commandes_banque(self, df):
        """Extrait les commandes d'un fichier BANQUE."""
        commandes = []
        for _, row in df.iterrows():
            try:
                commande = _normaliser_cmd(row.get(COLONNES_BANQUE["commande"]))
                montant  = row.get(COLONNES_BANQUE["montant"])
                if commande and montant:
                    montant = to_float(montant)
                    commandes.append({
                        "commande":      commande,
                        "montant":       montant,
                        "source":        "banque",
                        "date":          row.get(COLONNES_BANQUE["date"]),
                        "email":         row.get(COLONNES_BANQUE["email"]),
                        "type_paiement": row.get(COLONNES_BANQUE["type"]),
                        "statut":        row.get(COLONNES_BANQUE["statut"]),
                        "contrat":       row.get(COLONNES_BANQUE["contrat"]),
                        "n_remise":      row.get(COLONNES_BANQUE["remise"]),
                        "date_remise":   row.get(COLONNES_BANQUE["date_remise"]),
                    })
            except Exception as e:
                logger.error(f"Erreur ligne banque: {e}")
        logger.info(f"Banque : {len(commandes)} commandes extraites")
        return commandes

    def _extraire_commandes_alpilink(self, df):
        """Extrait les commandes d'un fichier ALPILINK."""
        commandes = []
        for _, row in df.iterrows():
            try:
                commande = _get_alpi_key(row)
                montant  = row.get(COLONNES_ALPILINK["montant"])
                if commande and montant:
                    montant = to_float(montant)
                    commandes.append({
                        "commande":   commande,
                        "montant":    montant,
                        "source":     "alpilink",
                        "statut":     row.get(COLONNES_ALPILINK["statut"]),
                        "canal":      row.get(COLONNES_ALPILINK["canal"]),
                        "id_portail": row.get(COLONNES_ALPILINK["id_portail"]),
                    })
            except Exception as e:
                logger.error(f"Erreur ligne Alpilink: {e}")
        logger.info(f"Alpilink : {len(commandes)} commandes extraites")
        return commandes

    def _extraire_commandes_compta(self, df):
        """Extrait les commandes d'un fichier COMPTA."""
        commandes = []
        sans_cmd  = []
        for _, row in df.iterrows():
            try:
                libelle  = row.get(COLONNES_COMPTA["piece"])
                montant  = row.get(COLONNES_COMPTA["montant"])
                date     = row.get(COLONNES_COMPTA["date"])
                journal  = row.get(COLONNES_COMPTA["journal"])
                commande = _normaliser_cmd(libelle)

                if commande and montant:
                    montant = to_float(montant)
                    commandes.append({
                        "commande": commande,
                        "montant":  montant,
                        "date":     date,
                        "source":   "compta",
                        "libelle":  row.get(COLONNES_COMPTA["libelle"]),
                        "journal":  journal,
                    })
                elif montant not in (None, '', 'nan'):
                    sans_cmd.append({
                        "Fichier": "compta",
                        "Libellé": str(libelle) if libelle else "",
                        "Montant": montant,
                        "Date":    date,
                        "Journal": journal,
                        "Erreur":  f"Libellé non reconnu : '{libelle}'"
                    })
            except Exception as e:
                logger.error(f"Erreur ligne compta: {e}")

        logger.info(f"Compta : {len(commandes)} commandes | {len(sans_cmd)} sans n° valide")
        return commandes, sans_cmd

    def _run(self, fichiers, dossier_sortie):
        """Exécution principale du traitement."""
        self.log("=== DÉBUT JUSTIFICATION ===")

        df_compta   = None
        df_banques  = []
        df_alpis    = []
        erreurs_fmt = []

        # ── PHASE 1 : CHARGEMENT ─────────────────────────────────────────
        total_fichiers = len(fichiers)
        for i, chemin in enumerate(fichiers, 1):
            nom = os.path.basename(chemin)
            self._progression(i, f"Chargement : {nom}")
            try:
                df = self._lire_fichier(chemin)
                if df is None:
                    erreurs_fmt.append({"Fichier": nom, "Erreur": "Format non supporté ou fichier corrompu"})
                    continue

                type_ = self._detecter_type(df)
                self.log(f"  [{type_.upper()}] {nom}")

                if type_ == 'compta':
                    df_compta = df
                elif type_ == 'banque':
                    df_banques.append(df)
                elif type_ == 'alpilink':
                    df_alpis.append(df)
                else:
                    erreurs_fmt.append({"Fichier": nom, "Erreur": "Type de fichier inconnu"})

            except Exception as e:
                erreurs_fmt.append({"Fichier": nom, "Erreur": str(e)})

        if df_compta is None:
            self.log("❌ Aucun fichier COMPTA détecté — abandon.")
            if self.callback_fin:
                self.callback_fin([], [], erreurs_fmt, [], [])
            return

        # ── PHASE 2 : EXTRACTION ─────────────────────────────────────────
        self._progression(total_fichiers + 1, "Extraction des commandes...")
        self.log(f"Compta: {len(df_compta)} lignes | Banques: {len(df_banques)} | Alpilink: {len(df_alpis)}")

        commandes_compta, erreurs_compta = self._extraire_commandes_compta(df_compta)
        erreurs_fmt.extend(erreurs_compta)

        commandes_banque = []
        for df in df_banques:
            commandes_banque.extend(self._extraire_commandes_banque(df))

        commandes_alpi = []
        for df in df_alpis:
            commandes_alpi.extend(self._extraire_commandes_alpilink(df))

        # ── PHASE 3 : RAPPROCHEMENT ───────────────────────────────────────
        self._progression(total_fichiers + 2, "Rapprochement en cours...")

        banque_dict = {cmd["commande"]: cmd for cmd in commandes_banque}
        alpi_dict   = {cmd["commande"]: cmd for cmd in commandes_alpi}

        validees    = []
        non_valides = []

        for cmd_compta in commandes_compta:
            num        = cmd_compta["commande"]
            cmd_banque = banque_dict.get(num)
            cmd_alpi   = alpi_dict.get(num)

            trouve_banque = cmd_banque is not None
            trouve_alpi   = cmd_alpi   is not None

            if trouve_banque and trouve_alpi:
                validees.append({
                    "commande":       num,
                    "montant_compta": cmd_compta["montant"],
                    "montant_banque": cmd_banque["montant"],
                    "montant_alpi":   cmd_alpi["montant"],
                    "ecart_banque":   round(abs(cmd_compta["montant"] - cmd_banque["montant"]), 2),
                    "ecart_alpi":     round(abs(cmd_compta["montant"] - cmd_alpi["montant"]),   2),
                    "source":         "banque + alpilink",
                    "date":           cmd_compta.get("date"),
                    "journal":        cmd_compta.get("journal"),
                    "statut":         "justifiée (banque + alpilink)",
                    "nom_pro":        cmd_alpi.get("nom_pro", ""),
                })
            elif trouve_banque:
                validees.append({
                    "commande":       num,
                    "montant_compta": cmd_compta["montant"],
                    "montant_banque": cmd_banque["montant"],
                    "montant_alpi":   None,
                    "ecart_banque":   round(abs(cmd_compta["montant"] - cmd_banque["montant"]), 2),
                    "ecart_alpi":     None,
                    "source":         "banque",
                    "date":           cmd_compta.get("date"),
                    "journal":        cmd_compta.get("journal"),
                    "statut":         "justifiée (banque)",
                    "nom_pro":        "",
                })
            elif trouve_alpi:
                validees.append({
                    "commande":       num,
                    "montant_compta": cmd_compta["montant"],
                    "montant_banque": None,
                    "montant_alpi":   cmd_alpi["montant"],
                    "ecart_banque":   None,
                    "ecart_alpi":     round(abs(cmd_compta["montant"] - cmd_alpi["montant"]), 2),
                    "source":         "alpilink",
                    "date":           cmd_compta.get("date"),
                    "journal":        cmd_compta.get("journal"),
                    "statut":         "justifiée (alpilink)",
                    "nom_pro":        cmd_alpi.get("nom_pro", ""),
                })
            else:
                non_valides.append({
                    "commande":       num,
                    "montant_compta": cmd_compta["montant"],
                    "montant_banque": None,
                    "montant_alpi":   None,
                    "ecart_banque":   None,
                    "ecart_alpi":     None,
                    "source":         "compta uniquement",
                    "date":           cmd_compta.get("date"),
                    "journal":        cmd_compta.get("journal"),
                    "statut":         "non justifiée",
                    "nom_pro":        "",
                })

        # ── PHASE 4 : EXPORT ──────────────────────────────────────────────
        self._progression(total_fichiers + 3, "Export Excel...")
        os.makedirs(dossier_sortie, exist_ok=True)
        chemin_rapport = os.path.join(dossier_sortie, "rapport_justification.xlsx")
        try:
            self._exporter(chemin_rapport, validees, non_valides, erreurs_fmt)
            self.log(f"✓ Rapport exporté : {chemin_rapport}")
        except Exception as e:
            self.log(f"✗ Erreur export: {e}")
            logger.error(f"Erreur export: {e}")

        self._progression(total_fichiers + 4, "Terminé ✓")
        self.log(
            f"✓ FIN — {len(validees)} justifiées | "
            f"{len(non_valides)} non justifiées | "
            f"{len(erreurs_fmt)} erreurs"
        )

        a_afficher_ecarts = [
            v for v in validees
            if (v["ecart_banque"] or 0) > 0 or (v["ecart_alpi"] or 0) > 0
        ]

        if self.callback_fin:
            self.callback_fin(
                a_afficher_ecarts,
                non_valides,
                erreurs_fmt,
                validees,
                non_valides
            )

    def _exporter(self, chemin, validees, non_valides, erreurs_fmt):
        """Exporte les résultats en Excel."""
        wb    = Workbook()
        VERT   = PatternFill("solid", fgColor="C6EFCE")
        JAUNE  = PatternFill("solid", fgColor="FFEB9C")
        ROUGE  = PatternFill("solid", fgColor="FFC7CE")
        ORANGE = PatternFill("solid", fgColor="FFD966")
        GRAS   = Font(bold=True)

        def ecrire_onglet(ws, lignes, fill_defaut, nom):
            if not lignes:
                ws.append(["(aucune ligne)"])
                return
            entetes = list(lignes[0].keys())
            ws.append(entetes)
            for cell in ws[1]:
                cell.font = GRAS
            for i, ligne in enumerate(lignes):
                try:
                    ws.append(list(ligne.values()))
                    row_ws = ws[ws.max_row]
                    if fill_defaut == VERT:
                        ecart_b = ligne.get("ecart_banque") or 0
                        ecart_a = ligne.get("ecart_alpi")   or 0
                        fill = JAUNE if (ecart_b > 0 or ecart_a > 0) else VERT
                    else:
                        fill = fill_defaut
                    for cell in row_ws:
                        cell.fill = fill
                except Exception as e:
                    logger.error(f"Erreur ligne {i} onglet {nom}: {e}")

        ws1 = wb.active
        ws1.title = "Validées"
        ecrire_onglet(ws1, validees, VERT, "Validées")

        ws2 = wb.create_sheet("Non justifiées")
        ecrire_onglet(ws2, non_valides, ROUGE, "Non justifiées")

        erreurs_libelles = [e for e in erreurs_fmt if "non reconnu" in e.get("Erreur", "")]
        erreurs_autres   = [e for e in erreurs_fmt if "non reconnu" not in e.get("Erreur", "")]

        ws3 = wb.create_sheet("Libellés inconnus")
        ecrire_onglet(ws3, erreurs_libelles, ORANGE, "Libellés inconnus")

        ws4 = wb.create_sheet("Erreurs format")
        ecrire_onglet(ws4, erreurs_autres, ORANGE, "Erreurs format")

        wb.save(chemin)
        logger.info("Export Excel terminé")
