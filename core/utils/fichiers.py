"""
Utilitaires pour la lecture et conversion de fichiers.
Centralise les fonctions de gestion de fichiers (lecture, écriture, archivage).
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, List
import chardet
import pandas as pd

from config import logger  # ← Utilisé pour les logs

# ============================================================================
# GESTION DE DOSSIERS
# ============================================================================

def creer_dossier(chemin: Union[Path, str]) -> Path:
    """
    Crée un dossier s'il n'existe pas.

    Args:
        chemin: Chemin du dossier (Path ou str)

    Returns:
        Path du dossier créé ou existant

    Exemple:
        >>> creer_dossier("fichiers_brut")
        Path("fichiers_brut")
    """
    chemin = Path(chemin)
    chemin.mkdir(parents=True, exist_ok=True)
    return chemin

# ============================================================================
# LISTAGE DE FICHIERS
# ============================================================================

def lister_fichiers_bruts(dossier: Union[Path, str]) -> List[Path]:
    """
    Liste les fichiers bruts supportés dans un dossier.

    Args:
        dossier: Chemin du dossier à scanner

    Returns:
        Liste triée des fichiers avec extensions .csv, .xls, .xlsx

    Exemple:
        >>> lister_fichiers_bruts("fichiers_brut")
        [Path("fichiers_brut/fichier1.csv"), Path("fichiers_brut/fichier2.xlsx")]
    """
    dossier = Path(dossier)
    if not dossier.exists():
        logger.warning(f"Dossier brut introuvable: {dossier}")
        return []

    extensions = {".csv", ".xls", ".xlsx"}
    return sorted(
        fichier
        for fichier in dossier.iterdir()
        if fichier.is_file() and fichier.suffix.lower() in extensions
    )

# ============================================================================
# GESTION DE FICHIERS
# ============================================================================

def supprimer_fichier(chemin: Union[Path, str]) -> bool:
    """
    Supprime un fichier s'il existe.

    Args:
        chemin: Chemin du fichier à supprimer

    Returns:
        True si succès, False si échec

    Exemple:
        >>> supprimer_fichier("fichiers_brut/ancien_fichier.csv")
        True
    """
    chemin = Path(chemin)
    try:
        if chemin.exists():
            chemin.unlink()
            logger.debug(f"Fichier supprimé: {chemin}")
        return True
    except OSError as e:
        logger.error(f"Erreur suppression fichier {chemin}: {e}")
        return False

def archiver_fichier(
    fichier: Union[Path, str],
    dossier_archive: Union[Path, str],
    creer_subdir_jour: bool = True
) -> Optional[Path]:
    """
    Déplace un fichier vers le dossier d'archive.

    Args:
        fichier: Fichier à archiver
        dossier_archive: Dossier de destination
        creer_subdir_jour: Si True, crée un sous-dossier par jour

    Returns:
        Path du fichier archivé ou None si échec

    Exemple:
        >>> archiver_fichier("fichiers_brut/test.csv", "archive")
        Path("archive/2026-06-02/test.csv")
    """
    fichier = Path(fichier)
    dossier_archive = Path(dossier_archive)

    if not fichier.exists():
        logger.warning(f"Fichier à archiver introuvable: {fichier}")
        return None

    try:
        if creer_subdir_jour:
            dossier_archive = dossier_archive / datetime.now().strftime("%Y-%m-%d")

        dossier_archive.mkdir(parents=True, exist_ok=True)
        destination = dossier_archive / fichier.name

        # Gérer les conflits de nom
        if destination.exists():
            horodatage = datetime.now().strftime("%H%M%S")
            destination = dossier_archive / f"{fichier.stem}_{horodatage}{fichier.suffix}"

        shutil.move(str(fichier), str(destination))
        logger.info(f"Fichier archivé: {destination}")
        return destination

    except OSError as e:
        logger.error(f"Erreur archivage {fichier}: {e}")
        return None

# ============================================================================
# LECTURE DE FICHIERS
# ============================================================================

def lire_csv(
    chemin: Union[Path, str],
    sep: str = ";",
    encoding: str = "utf-8",
    header: int = 0
) -> Optional[pd.DataFrame]:
    """
    Lit un fichier CSV de manière robuste.

    Args:
        chemin: Chemin du fichier CSV
        sep: Séparateur (défaut: ";")
        encoding: Encodage (défaut: "utf-8")
        header: Ligne d'en-tête (défaut: 0)

    Returns:
        DataFrame ou None si échec

    Exemple:
        >>> lire_csv("fichiers_brut/test.csv")
        pd.DataFrame(...)
    """
    try:
        df = pd.read_csv(
            Path(chemin),
            sep=sep,
            encoding=encoding,
            header=header,
            dtype=str,
            on_bad_lines='warn'
        )
        logger.debug(f"Fichier CSV lu: {chemin} ({len(df)} lignes)")
        return df
    except Exception as e:
        logger.error(f"Erreur lecture CSV {chemin}: {e}")
        return None

def lire_xlsx(
    chemin: Union[Path, str],
    header: int = 0,
    sheet_name: Union[int, str] = 0
) -> Optional[pd.DataFrame]:
    """
    Lit un fichier XLSX de manière robuste.

    Args:
        chemin: Chemin du fichier XLSX
        header: Ligne d'en-tête (défaut: 0)
        sheet_name: Nom ou index de la feuille (défaut: 0)

    Returns:
        DataFrame ou None si échec

    Exemple:
        >>> lire_xlsx("fichiers_brut/test.xlsx")
        pd.DataFrame(...)
    """
    try:
        df = pd.read_excel(
            Path(chemin),
            header=header,
            sheet_name=sheet_name,
            engine='openpyxl',
            dtype=str
        )
        logger.debug(f"Fichier XLSX lu: {chemin} ({len(df)} lignes)")
        return df
    except Exception as e:
        logger.error(f"Erreur lecture XLSX {chemin}: {e}")
        return None

def lire_xls(
    chemin: Union[Path, str],
    header: int = 0
) -> Optional[pd.DataFrame]:
    """
    Lit un fichier XLS (ancien format Excel) et le convertit en DataFrame.

    Args:
        chemin: Chemin du fichier XLS
        header: Ligne d'en-tête (défaut: 0)

    Returns:
        DataFrame ou None si échec

    Exemple:
        >>> lire_xls("fichiers_brut/ancien.xls")
        pd.DataFrame(...)
    """
    try:
        df = pd.read_excel(
            Path(chemin),
            header=header,
            engine='xlrd',
            dtype=str
        )
        logger.debug(f"Fichier XLS lu: {chemin} ({len(df)} lignes)")
        return df
    except Exception as e:
        logger.error(f"Erreur lecture XLS {chemin}: {e}")
        return None

# ============================================================================
# CONVERSION DE FICHIERS
# ============================================================================

def convertir_xls_en_xlsx(fichier: Union[Path, str]) -> Path:
    """
    Convertit un fichier .xls en .xlsx avec openpyxl.

    Si le fichier .xlsx existe déjà, il est retourné directement.

    Args:
        fichier: Chemin du fichier .xls à convertir

    Returns:
        Path du fichier .xlsx converti

    Raises:
        FileNotFoundError: Si le fichier source est introuvable
        RuntimeError: Si la conversion échoue

    Exemple:
        >>> convertir_xls_en_xlsx("fichiers_brut/ancien.xls")
        Path("fichiers_brut/ancien.xlsx")
    """
    fichier = Path(fichier)

    if fichier.suffix.lower() != ".xls":
        logger.warning(f"convertir_xls_en_xlsx appelé sur un fichier non .xls : {fichier.name}")
        return fichier

    if not fichier.exists():
        raise FileNotFoundError(f"Fichier source introuvable : {fichier}")

    nouveau = fichier.with_suffix(".xlsx")

    if nouveau.exists():
        logger.debug(f"Fichier déjà converti, réutilisation : {nouveau.name}")
        return nouveau

    logger.info(f"Conversion XLS → XLSX : {fichier.name}")

    try:
        df = pd.read_excel(
            fichier,
            sheet_name=0,
            header=None,
            engine="xlrd",
            dtype=str
        )

        with pd.ExcelWriter(nouveau, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False, header=False)

        logger.info(f"✅ Conversion réussie : {nouveau.name}")

    except Exception as e:
        logger.error(f"❌ Échec conversion {fichier.name} : {e}")
        raise RuntimeError(f"Impossible de convertir {fichier.name} en xlsx : {e}") from e

    return nouveau

# ============================================================================
# DÉTECTION & CONVERSION D'ENCODING
# ============================================================================

def detecter_encoding(fichier: Union[Path, str], fallback: str = "utf-8") -> str:
    """
    Détecte l'encodage d'un fichier avec chardet.

    Args:
        fichier: Chemin du fichier
        fallback: Encodage par défaut si détection échoue

    Returns:
        Nom de l'encodage détecté

    Exemple:
        >>> detecter_encoding("fichiers_brut/test.csv")
        'utf-8'
    """
    fichier = Path(fichier)

    if not fichier.exists():
        return fallback

    try:
        with open(fichier, "rb") as f:
            raw = f.read(100000)  # Lire max 100KB

        result = chardet.detect(raw)

        if result and result.get("encoding"):
            encoding = result["encoding"]
            confidence = result.get("confidence", 0)
            logger.debug(f"Encodage détecté : {encoding} ({confidence:.1%})")
            return encoding

        return fallback

    except Exception as err:
        logger.warning(f"Erreur détection encodage : {err}, fallback={fallback}")
        return fallback

def convertir_encoding(
    fichier: Union[Path, str],
    encoding_source: Optional[str] = None,
    encoding_cible: str = "utf-8"
) -> Path:
    """
    Convertit l'encoding d'un fichier CSV/TXT.

    Le fichier original est remplacé avec le nouvel encoding.

    Args:
        fichier: Chemin du fichier à convertir
        encoding_source: Encoding source (auto-détecté si None)
        encoding_cible: Encoding cible (utf-8 par défaut)

    Returns:
        Chemin du fichier converti

    Exemple:
        >>> convertir_encoding("fichier.csv")  # Auto-détecte + convertit en UTF-8
        Path("fichier.csv")
    """
    fichier = Path(fichier)

    if not fichier.exists():
        logger.error(f"[ENCODING] Fichier introuvable : {fichier}")
        return fichier

    # Déterminer l'encoding source
    if encoding_source is None:
        encoding_source = detecter_encoding(fichier)
        if encoding_source is None:
            logger.warning(f"[ENCODING] Impossible de détecter l'encoding pour {fichier.name}")
            return fichier

    # Si déjà en UTF-8, rien à faire
    if encoding_source.lower() == encoding_cible.lower():
        logger.debug(f"[ENCODING] {fichier.name} est déjà en {encoding_cible}")
        return fichier

    try:
        # Lire avec l'encoding source
        with open(fichier, 'r', encoding=encoding_source, errors='replace') as f:
            contenu = f.read()

        # Écrire avec l'encoding cible
        with open(fichier, 'w', encoding=encoding_cible, errors='replace') as f:
            f.write(contenu)

        logger.info(f"[ENCODING] ✅ {fichier.name} converti : {encoding_source} → {encoding_cible}")
        return fichier

    except Exception as e:
        logger.error(f"[ENCODING] Erreur conversion {fichier.name} : {e}")
        return fichier

def normaliser_latin1_en_utf8(texte: str) -> str:
    """
    Convertit les caractères latin-1 mal encodés en UTF-8.

    Exemple : 'cr\x82ation' → 'création'

    Args:
        texte: Texte à normaliser

    Returns:
        Texte normalisé
    """
    try:
        # Encoder en latin-1, décoder en UTF-8
        if isinstance(texte, str):
            return texte.encode('latin-1', errors='replace').decode('utf-8', errors='replace')
        return texte
    except (UnicodeDecodeError, AttributeError) as e:
        logger.debug(f"Normalisation latin1→utf8 échouée: {e}")
        return texte

# ============================================================================
# FONCTIONS SPÉCIFIQUES POUR LES HANDLERS MODULE 1
# ============================================================================

def creer_dossier_sortie(dossier_parent: Union[Path, str]) -> Path:
    """
    Crée le dossier de sortie pour les fichiers transformés.

    Args:
        dossier_parent: Dossier parent où créer le dossier de sortie

    Returns:
        Path du dossier de sortie créé

    Exemple:
        >>> creer_dossier_sortie("fichiers_brut")
        Path("fichiers_brut/sortie")
    """
    dossier_sortie = Path(dossier_parent) / "sortie"
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    return dossier_sortie

def ecriture_csv(chemin: Union[Path, str], df: pd.DataFrame) -> None:
    """
    Écrit un DataFrame dans un fichier CSV avec le bon format.

    Args:
        chemin: Chemin du fichier CSV à écrire
        df: DataFrame à écrire

    Exemple:
        >>> ecriture_csv("sortie/test.csv", df)
    """
    chemin = Path(chemin)
    try:
        df.to_csv(
            chemin,
            sep=";",
            index=False,
            encoding="utf-8",
            float_format="%.2f"
        )
        logger.debug(f"CSV écrit : {chemin} ({len(df)} lignes)")
    except Exception as e:
        logger.error(f"Erreur écriture CSV {chemin}: {e}")
        raise

__all__ = [
    "creer_dossier",
    "lister_fichiers_bruts",
    "supprimer_fichier",
    "archiver_fichier",
    "lire_csv",
    "lire_xlsx",
    "lire_xls",
    "convertir_xls_en_xlsx",
    "detecter_encoding",
    "convertir_encoding",
    "normaliser_latin1_en_utf8",
    "creer_dossier_sortie",
    "ecriture_csv",
]
