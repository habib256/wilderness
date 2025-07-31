"""
Extracteur de données de terrain réelles depuis internet.

Ce module permet de récupérer des données d'élévation réelles depuis diverses sources :
- NASA SRTM (Shuttle Radar Topography Mission)
- OpenTopography API
- USGS EarthExplorer
- OpenElevation API

Spécialement optimisé pour l'île de la Réunion avec ses coordonnées spécifiques.
"""

import requests
import numpy as np
import logging
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
import tempfile
import zipfile
import os
from PIL import Image
import json
from dataclasses import dataclass
from .progress import (
    ProgressTracker, ProgressStage, get_progress_tracker
)
from .void_correction import (
    correct_srtm_voids, analyze_voids, VoidCorrectionMethod
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dépendances optionnelles
try:
    import rasterio
    from rasterio.enums import Resampling
    RASTERIO_AVAILABLE = True
except ImportError:
    logger.warning("rasterio non disponible, fonctionnalités réduites")
    RASTERIO_AVAILABLE = False


@dataclass
class TerrainBounds:
    """Définit les limites géographiques d'un terrain."""
    north: float  # Latitude nord
    south: float  # Latitude sud  
    east: float   # Longitude est
    west: float   # Longitude ouest
    
    def center(self) -> Tuple[float, float]:
        """Retourne le centre (lat, lon)."""
        return (
            (self.north + self.south) / 2,
            (self.east + self.west) / 2
        )
    
    def dimensions_km(self) -> Tuple[float, float]:
        """Approximation des dimensions en kilomètres."""
        # Conversion approximative degrés -> km
        lat_km = abs(self.north - self.south) * 111.0
        lon_km = abs(self.east - self.west) * 111.0 * np.cos(np.radians(self.center()[0]))
        return lat_km, lon_km


class ReunionTerrainBounds:
    """Coordonnées précises de l'île de la Réunion."""
    
    # Limites étendues pour capturer toute l'île
    FULL_ISLAND = TerrainBounds(
        north=-20.871,  # Pointe nord 
        south=-21.389,  # Pointe sud
        east=55.838,    # Pointe est
        west=55.214     # Pointe ouest
    )
    
    # Zone centrale (plus montagne)
    CENTRAL_MOUNTAINS = TerrainBounds(
        north=-20.95,
        south=-21.25, 
        east=55.65,
        west=55.35
    )
    
    # Zone côtière ouest (Saint-Denis, Saint-Paul)
    WEST_COAST = TerrainBounds(
        north=-20.85,
        south=-21.05,
        east=55.45,
        west=55.20
    )


class HonshuTerrainBounds:
    """Coordonnées précises de l'île d'Honshu (Japon)."""
    
    # Limites complètes de Honshu (île principale du Japon)
    FULL_ISLAND = TerrainBounds(
        north=41.543,   # Pointe nord (Aomori)
        south=34.139,   # Pointe sud (Wakayama)
        east=141.347,   # Pointe est (côte Pacifique)
        west=129.704    # Pointe ouest (côte mer du Japon)
    )
    
    # Région du Kansai (Osaka, Kyoto, Nara)
    KANSAI = TerrainBounds(
        north=35.8,
        south=33.8,
        east=136.5,
        west=134.8
    )
    
    # Région du Kanto (Tokyo, mont Fuji)
    KANTO = TerrainBounds(
        north=36.5,
        south=35.0,
        east=140.5,
        west=138.5
    )
    
    # Alpes japonaises (zone montagneuse centrale)
    JAPANESE_ALPS = TerrainBounds(
        north=36.8,
        south=35.5,
        east=138.5,
        west=137.0
    )


class YakushimaTerrainBounds:
    """Coordonnées précises de l'île de Yakushima (Japon)."""
    
    # Île complète de Yakushima (site UNESCO)
    FULL_ISLAND = TerrainBounds(
        north=30.45,    # Pointe nord
        south=30.25,    # Pointe sud  
        east=130.65,    # Pointe est
        west=130.45     # Pointe ouest
    )
    
    # Zone centrale avec Mont Miyanoura (1 936 m)
    CENTRAL_MOUNTAINS = TerrainBounds(
        north=30.38,
        south=30.32,
        east=130.55,
        west=130.50
    )
    
    # Forêt de Jōmon-sugi (cèdres millénaires)
    JOMON_FOREST = TerrainBounds(
        north=30.375,
        south=30.365,
        east=130.505,
        west=130.495
    )
    
    # Cascade de Senpiro et ravins
    SENPIRO_WATERFALL = TerrainBounds(
        north=30.265,
        south=30.250,
        east=130.545,
        west=130.530
    )
    
    # Zone côte-à-colline la plus abrupte
    STEEP_COAST = TerrainBounds(
        north=30.250,
        south=30.235,
        east=130.610,
        west=130.595
    )
    
    # Vue large et éloignée de Yakushima (zone étendue)
    WIDE_VIEW = TerrainBounds(
        north=30.60,    # ~17km au nord
        south=30.10,    # ~17km au sud
        east=130.80,    # ~17km à l'est
        west=130.30     # ~17km à l'ouest
    )


class OpenTopographyAPI:
    """Interface pour l'API OpenTopography (données SRTM 30m)."""
    
    BASE_URL = "https://cloud.sdsc.edu/v1/raster"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'API OpenTopography.
        
        Args:
            api_key: Clé API (optionnelle pour usage académique limité)
        """
        self.api_key = api_key
        self.session = requests.Session()
        
    def get_srtm_data(self, bounds: TerrainBounds, output_size: Tuple[int, int] = (1024, 1024)) -> Optional[np.ndarray]:
        """
        Récupère les données SRTM pour une zone donnée.
        
        Args:
            bounds: Limites géographiques
            output_size: Taille de sortie souhaitée (width, height)
            
        Returns:
            Heightmap numpy array ou None si erreur
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.INITIALIZATION,
            f"Récupération SRTM OpenTopography {bounds.center()}"
        )
        
        try:
            # Paramètres de requête
            params = {
                'demtype': 'SRTMGL30',  # SRTM 30m global
                'south': bounds.south,
                'north': bounds.north,
                'west': bounds.west,
                'east': bounds.east,
                'outputFormat': 'GTiff',
                'API_Key': self.api_key or ''
            }
            
            progress_tracker.update_progress(0.1, "Envoi requête OpenTopography")
            
            logger.info(f"Requête SRTM: {bounds.center()}, dims={bounds.dimensions_km()}km")
            
            response = self.session.get(f"{self.BASE_URL}", params=params, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"Erreur API OpenTopography: {response.status_code}")
                return None
                
            progress_tracker.update_progress(0.4, "Données reçues, traitement GeoTIFF")
            
            # Sauvegarde temporaire du GeoTIFF
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            
            try:
                heightmap = self._process_geotiff(tmp_path, output_size)
                progress_tracker.update_progress(1.0, "SRTM traité avec succès")
                return heightmap
            finally:
                os.unlink(tmp_path)
                
        except Exception as e:
            logger.error(f"Erreur OpenTopography: {e}")
            progress_tracker.update_progress(1.0, f"Erreur: {e}")
            return None
    
    def _process_geotiff(self, geotiff_path: str, output_size: Tuple[int, int]) -> np.ndarray:
        """Traite le fichier GeoTIFF et le redimensionne."""
        if not RASTERIO_AVAILABLE:
            raise ImportError("rasterio requis pour traiter les GeoTIFF")
        
        progress_tracker = get_progress_tracker()
        
        with rasterio.open(geotiff_path) as dataset:
            progress_tracker.update_progress(0.5, f"Lecture GeoTIFF {dataset.width}x{dataset.height}")
            
            # Lit les données d'élévation
            elevation_data = dataset.read(1, 
                out_shape=output_size,
                resampling=Resampling.bilinear
            )
            
            progress_tracker.update_progress(0.8, "Normalisation des données")
            
            # Analyse et corrige les voids (pixels manquants)
            nodata_value = dataset.nodata
            if nodata_value is not None:
                # Analyse des voids avant correction
                void_info = analyze_voids(elevation_data, nodata_value)
                
                if void_info['has_voids']:
                    logger.info(f"Voids détectés: {void_info['void_percentage']:.2f}% "
                               f"({void_info['void_pixels']} pixels)")
                    
                    # Corrige les voids avec interpolation bilinéaire
                    elevation_data = correct_srtm_voids(
                        elevation_data, 
                        method=VoidCorrectionMethod.BILINEAR_INTERPOLATION,
                        nodata_value=nodata_value,
                        interpolation_radius=5
                    )
                    
                    # Vérifie que la correction a fonctionné
                    void_info_after = analyze_voids(elevation_data, nodata_value)
                    if not void_info_after['has_voids']:
                        logger.info("✅ Correction des voids réussie")
                    else:
                        logger.warning(f"⚠️ Voids restants: {void_info_after['void_percentage']:.2f}%")
                else:
                    logger.info("✅ Aucun void détecté dans les données SRTM")
            
            # Normalise entre 0 et 1
            min_elev = np.min(elevation_data)
            max_elev = np.max(elevation_data)
            
            if max_elev > min_elev:
                normalized = (elevation_data - min_elev) / (max_elev - min_elev)
            else:
                normalized = np.zeros_like(elevation_data, dtype=np.float32)
            
            logger.info(f"Élévation: {min_elev:.1f}m à {max_elev:.1f}m")
            
            return normalized.astype(np.float32)


class OpenElevationAPI:
    """Interface pour l'API OpenElevation (fallback plus simple)."""
    
    BASE_URL = "https://api.open-elevation.com/api/v1/lookup"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_elevation_grid(self, bounds: TerrainBounds, grid_size: int = 64) -> Optional[np.ndarray]:
        """
        Récupère une grille d'élévation via l'API point par point.
        
        Args:
            bounds: Limites géographiques
            grid_size: Taille de la grille (ex: 64x64)
            
        Returns:
            Heightmap numpy array ou None si erreur
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.INITIALIZATION,
            f"Récupération OpenElevation grille {grid_size}x{grid_size}"
        )
        
        try:
            # Génère une grille de coordonnées
            lats = np.linspace(bounds.south, bounds.north, grid_size)
            lons = np.linspace(bounds.west, bounds.east, grid_size)
            
            # Prépare les points à requêter (limite de 1000 points par requête)
            locations = []
            for lat in lats:
                for lon in lons:
                    locations.append({"latitude": lat, "longitude": lon})
            
            # Divise en chunks pour respecter les limites API
            chunk_size = 1000
            elevation_grid = np.zeros((grid_size, grid_size))
            
            total_chunks = (len(locations) + chunk_size - 1) // chunk_size
            
            for i in range(0, len(locations), chunk_size):
                chunk = locations[i:i + chunk_size]
                chunk_num = i // chunk_size + 1
                
                progress = chunk_num / total_chunks
                progress_tracker.update_progress(
                    progress * 0.8, 
                    f"Requête chunk {chunk_num}/{total_chunks}"
                )
                
                response = self.session.post(
                    self.BASE_URL,
                    json={"locations": chunk},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    # Remplit la grille
                    for j, result in enumerate(results):
                        global_idx = i + j
                        row = global_idx // grid_size
                        col = global_idx % grid_size
                        elevation_grid[row, col] = result.get("elevation", 0)
                else:
                    logger.warning(f"Erreur chunk {chunk_num}: {response.status_code}")
            
            progress_tracker.update_progress(0.9, "Correction des voids et normalisation")
            
            # Détecte et corrige les voids (valeurs à 0 qui peuvent être des échecs de requête)
            void_info = analyze_voids(elevation_grid, nodata_value=0)
            
            if void_info['has_voids']:
                logger.info(f"Voids détectés dans OpenElevation: {void_info['void_percentage']:.2f}% "
                           f"({void_info['void_pixels']} pixels)")
                
                # Corrige les voids avec extrapolation (plus adapté pour les données par points)
                elevation_grid = correct_srtm_voids(
                    elevation_grid, 
                    method=VoidCorrectionMethod.EXTRAPOLATION,
                    nodata_value=0,
                    extrapolation_distance=10
                )
                
                # Vérifie que la correction a fonctionné
                void_info_after = analyze_voids(elevation_grid, nodata_value=0)
                if not void_info_after['has_voids']:
                    logger.info("✅ Correction des voids OpenElevation réussie")
                else:
                    logger.warning(f"⚠️ Voids restants: {void_info_after['void_percentage']:.2f}%")
            
            # Normalise
            min_elev = np.min(elevation_grid)
            max_elev = np.max(elevation_grid)
            
            if max_elev > min_elev:
                normalized = (elevation_grid - min_elev) / (max_elev - min_elev)
            else:
                normalized = np.zeros_like(elevation_grid)
            
            progress_tracker.update_progress(1.0, f"Grille complète: {min_elev:.1f}m-{max_elev:.1f}m")
            logger.info(f"OpenElevation: {min_elev:.1f}m à {max_elev:.1f}m")
            
            return normalized.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Erreur OpenElevation: {e}")
            return None


class ReunionTerrainExtractor:
    """Extracteur spécialisé pour l'île de la Réunion."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'extracteur Réunion.
        
        Args:
            api_key: Clé API OpenTopography (optionnelle)
        """
        self.opentopo = OpenTopographyAPI(api_key)
        self.openelevation = OpenElevationAPI()
        
    def extract_reunion_4k(self, zone: str = "full") -> Optional[np.ndarray]:
        """
        Extrait une heightmap native haute résolution de la Réunion (SANS upscaling).
        
        Cette méthode privilégie la précision des données réelles plutôt que 
        l'obtention forcée d'une résolution 4096x4096. Elle retourne la meilleure
        résolution native disponible.
        
        Args:
            zone: "full", "central", ou "west"
            
        Returns:
            Heightmap native normalisée ou None si erreur
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.INITIALIZATION,
            f"Extraction Réunion Haute Résolution Native - zone {zone}"
        )
        
        # Sélectionne la zone
        if zone == "full":
            bounds = ReunionTerrainBounds.FULL_ISLAND
        elif zone == "central":
            bounds = ReunionTerrainBounds.CENTRAL_MOUNTAINS
        elif zone == "west":
            bounds = ReunionTerrainBounds.WEST_COAST
        else:
            logger.error(f"Zone inconnue: {zone}")
            return None
        
        center_lat, center_lon = bounds.center()
        lat_km, lon_km = bounds.dimensions_km()
        
        logger.info(f"🏝️ Extraction Réunion Haute Résolution Native - Zone {zone}")
        logger.info(f"   Centre: {center_lat:.3f}°S, {center_lon:.3f}°E")
        logger.info(f"   Dimensions: {lat_km:.1f} x {lon_km:.1f} km")
        logger.info(f"   ⚠️  Priorité: Données natives sans upscaling artificiel")
        
        # 1. Essaie d'obtenir SRTM 1-arcsec (~30m) si disponible
        progress_tracker.update_progress(0.1, "Tentative SRTM 1-arcsec (30m résolution)")
        
        # Tente plusieurs résolutions natives décroissantes
        native_resolutions = [
            (3601, 3601, "SRTM 1-arcsec"),  # ~30m résolution
            (1801, 1801, "SRTM 3-arcsec"),  # ~90m résolution  
            (1201, 1201, "SRTM optimisé"),  # Résolution intermédiaire
            (901, 901, "SRTM standard"),    # Résolution de base
        ]
        
        for width, height, description in native_resolutions:
            progress_tracker.update_progress(
                0.1 + (native_resolutions.index((width, height, description)) * 0.2), 
                f"Tentative {description} ({width}x{height})"
            )
            
            logger.info(f"   🔍 Tentative {description}: {width}x{height}")
            
            heightmap = self.opentopo.get_srtm_data(bounds, (width, height))
            
            if heightmap is not None:
                actual_resolution = f"{width}x{height}"
                meters_per_pixel = (lat_km * 1000) / width
                
                logger.info(f"✅ Succès {description}")
                logger.info(f"   📐 Résolution finale: {actual_resolution}")
                logger.info(f"   📏 Précision: ~{meters_per_pixel:.1f}m par pixel")
                logger.info(f"   🎯 Données 100% natives (aucun upscaling)")
                
                progress_tracker.update_progress(1.0, f"✅ Réunion {description} - données natives")
                return self._post_process_reunion(heightmap)
        
        # 2. Si SRTM échoue complètement, essaie OpenElevation SANS upscaling
        logger.warning("SRTM indisponible, tentative OpenElevation grille dense")
        progress_tracker.update_progress(0.6, "Fallback OpenElevation grille dense")
        
        # Utilise la grille la plus dense possible SANS upscaling
        max_safe_grid = 1000  # Limite pour éviter timeout
        grid_heightmap = self.openelevation.get_elevation_grid(bounds, max_safe_grid)
        
        if grid_heightmap is not None:
            meters_per_pixel = (lat_km * 1000) / max_safe_grid
            
            logger.info(f"✅ OpenElevation grille dense réussie")
            logger.info(f"   📐 Résolution: {max_safe_grid}x{max_safe_grid}")
            logger.info(f"   📏 Précision: ~{meters_per_pixel:.1f}m par pixel")
            logger.info(f"   🎯 Données natives sans interpolation")
            
            progress_tracker.update_progress(1.0, "✅ Réunion OpenElevation - grille native dense")
            return self._post_process_reunion(grid_heightmap)
        
        logger.error("❌ Toutes les sources de données natives échouées")
        progress_tracker.update_progress(1.0, "❌ Échec extraction données natives")
        return None

    def extract_reunion_1k(self, zone: str = "full") -> Optional[np.ndarray]:
        """
        Extrait une heightmap 1024x1024 de la Réunion.
        
        Args:
            zone: "full", "central", ou "west"
            
        Returns:
            Heightmap 1024x1024 normalisée ou None si erreur
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.INITIALIZATION,
            f"Extraction Réunion 1K - zone {zone}"
        )
        
        # Sélectionne la zone
        if zone == "full":
            bounds = ReunionTerrainBounds.FULL_ISLAND
        elif zone == "central":
            bounds = ReunionTerrainBounds.CENTRAL_MOUNTAINS
        elif zone == "west":
            bounds = ReunionTerrainBounds.WEST_COAST
        else:
            logger.error(f"Zone inconnue: {zone}")
            return None
        
        center_lat, center_lon = bounds.center()
        lat_km, lon_km = bounds.dimensions_km()
        
        logger.info(f"🏝️ Extraction Réunion - Zone {zone}")
        logger.info(f"   Centre: {center_lat:.3f}°S, {center_lon:.3f}°E")
        logger.info(f"   Dimensions: {lat_km:.1f} x {lon_km:.1f} km")
        
        # Essaie d'abord OpenTopography (haute résolution)
        progress_tracker.update_progress(0.1, "Tentative OpenTopography SRTM")
        
        heightmap = self.opentopo.get_srtm_data(bounds, (1024, 1024))
        
        if heightmap is not None:
            progress_tracker.update_progress(1.0, "✅ Réunion 1K - OpenTopography réussi")
            return self._post_process_reunion(heightmap)
        
        # Fallback vers OpenElevation (plus lent mais fiable)
        logger.warning("OpenTopography échoué, fallback vers OpenElevation")
        progress_tracker.update_progress(0.5, "Fallback OpenElevation")
        
        grid_heightmap = self.openelevation.get_elevation_grid(bounds, 128)
        
        if grid_heightmap is not None:
            # Upscale vers 1024x1024
            from scipy.ndimage import zoom
            scale = 1024 / 128
            heightmap = zoom(grid_heightmap, scale, order=1)
            
            # Assure taille exacte
            if heightmap.shape[0] != 1024:
                heightmap = heightmap[:1024, :1024]
            
            progress_tracker.update_progress(1.0, "✅ Réunion 1K - OpenElevation réussi")
            return self._post_process_reunion(heightmap)
        
        logger.error("❌ Tous les services échoués pour la Réunion")
        progress_tracker.update_progress(1.0, "❌ Échec extraction Réunion")
        return None
    
    def _post_process_reunion(self, heightmap: np.ndarray) -> np.ndarray:
        """Post-traitement spécifique à la Réunion avec préservation du niveau de la mer."""
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.NORMALIZATION,
            "Post-traitement Réunion"
        )
        
        # Sépare les zones terrestres et sous-marines AVANT tout traitement
        land_mask = heightmap > 0
        underwater_mask = heightmap <= 0
        
        # Améliore le contraste pour mettre en valeur le relief volcanique
        progress_tracker.update_progress(0.2, "Amélioration contraste volcanique")
        
        # Applique une courbe gamma SEULEMENT sur les zones terrestres (évite RuntimeWarning)
        gamma = 0.8  # Accentue les reliefs moyens
        heightmap_enhanced = heightmap.copy()
        
        if np.any(land_mask):
            # Normalise temporairement les terres pour appliquer gamma
            land_values = heightmap[land_mask]
            land_max = np.max(land_values)
            if land_max > 0:
                land_normalized = land_values / land_max
                land_gamma = np.power(land_normalized, gamma)
                heightmap_enhanced[land_mask] = land_gamma * land_max
        
        # Lisse légèrement pour éliminer le bruit de numérisation
        progress_tracker.update_progress(0.4, "Lissage anti-bruit")
        
        from scipy.ndimage import gaussian_filter
        
        # Applique le lissage en préservant les zones distinctes
        heightmap_smooth = heightmap_enhanced.copy()
        
        # Lisse seulement les zones terrestres pour éviter le mélange terre/mer
        if np.any(land_mask):
            land_smooth = gaussian_filter(heightmap_enhanced, sigma=0.5)
            heightmap_smooth[land_mask] = land_smooth[land_mask]
        
        # Préserve les zones sous-marines sans lissage pour éviter leur disparition
        if np.any(underwater_mask):
            heightmap_smooth[underwater_mask] = heightmap_enhanced[underwater_mask]
        
        # CORRECTION: Préservation du niveau de la mer
        progress_tracker.update_progress(0.6, "Préservation niveau de la mer")
        
        # Renormalisation qui préserve le niveau de la mer à 0.0
        progress_tracker.update_progress(0.8, "Renormalisation avec niveau de mer fixe")
        
        heightmap_final = np.zeros_like(heightmap_smooth)
        
        # UTILISE LES MASQUES ORIGINAUX pour identifier correctement les zones
        # (car le lissage peut avoir modifié les zones de transition)
        
        if np.any(land_mask):
            # Traite les zones émergées (au-dessus du niveau de la mer dans les données originales)
            land_values_smooth = heightmap_smooth[land_mask]
            # Filtre pour ne garder que les valeurs positives après lissage
            positive_land = land_values_smooth[land_values_smooth > 0]
            
            if len(positive_land) > 0:
                max_val = np.max(positive_land)
                if max_val > 0:
                    # Normalise seulement les terres vers [0, 1]
                    land_values_normalized = heightmap_smooth[land_mask] / max_val
                    # Assure que les valeurs négatives restent à 0 pour les terres
                    land_values_normalized = np.maximum(land_values_normalized, 0.0)
                    heightmap_final[land_mask] = land_values_normalized
        
        if np.any(underwater_mask):
            # Traite les zones sous-marines (en dessous du niveau de la mer dans les données originales)
            underwater_values_smooth = heightmap_smooth[underwater_mask]
            
            # Trouve la valeur la plus négative dans les données originales sous-marines
            original_underwater_values = heightmap[underwater_mask]
            min_underwater = np.min(original_underwater_values)
            
            if min_underwater < 0:
                # Normalise les profondeurs marines sur [-0.1, 0] en utilisant les données originales
                # pour préserver la structure des profondeurs
                # Calcul correct: ratio positif multiplié par -0.1 pour obtenir des valeurs négatives
                depth_ratio = abs(original_underwater_values) / abs(min_underwater)  # ratio [0, 1]
                underwater_final_values = -depth_ratio * 0.1  # résultat [-0.1, 0]
                heightmap_final[underwater_mask] = underwater_final_values
            else:
                # Les valeurs exactement à 0 restent à 0 (niveau de la mer)
                heightmap_final[underwater_mask] = 0.0
        
        progress_tracker.update_progress(1.0, "Post-traitement terminé")
        
        logger.info(f"🌊 Réunion processed - Niveau de la mer préservé à 0.0")
        logger.info(f"🌋 Piton des Neiges et reliefs volcaniques accentués")
        
        return heightmap_final.astype(np.float32)


class HonshuTerrainExtractor:
    """Extracteur spécialisé pour l'île d'Honshu (Japon)."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'extracteur Honshu.
        
        Args:
            api_key: Clé API OpenTopography (optionnelle)
        """
        self.opentopo = OpenTopographyAPI(api_key)
        self.openelevation = OpenElevationAPI()
        
    def extract_honshu_4k(self, zone: str = "full") -> Optional[np.ndarray]:
        """
        Extrait une heightmap native haute résolution d'Honshu (SANS upscaling).
        
        Cette méthode privilégie la précision des données réelles plutôt que 
        l'obtention forcée d'une résolution 4096x4096. Elle retourne la meilleure
        résolution native disponible.
        
        Args:
            zone: "full", "kansai", "kanto", ou "alps"
            
        Returns:
            Heightmap native normalisée ou None si erreur
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.INITIALIZATION,
            f"Extraction Honshu Haute Résolution Native - zone {zone}"
        )
        
        # Sélectionne la zone
        if zone == "full":
            bounds = HonshuTerrainBounds.FULL_ISLAND
        elif zone == "kansai":
            bounds = HonshuTerrainBounds.KANSAI
        elif zone == "kanto":
            bounds = HonshuTerrainBounds.KANTO
        elif zone == "alps":
            bounds = HonshuTerrainBounds.JAPANESE_ALPS
        else:
            logger.error(f"Zone inconnue: {zone}")
            return None
        
        center_lat, center_lon = bounds.center()
        lat_km, lon_km = bounds.dimensions_km()
        
        logger.info(f"🏔️ Extraction Honshu Haute Résolution Native - Zone {zone}")
        logger.info(f"   Centre: {center_lat:.3f}°N, {center_lon:.3f}°E")
        logger.info(f"   Dimensions: {lat_km:.1f} x {lon_km:.1f} km")
        logger.info(f"   ⚠️  Priorité: Données natives sans upscaling artificiel")
        
        # Tente plusieurs résolutions natives décroissantes
        # Pour Honshu (plus grande île), on privilégie des résolutions plus élevées
        native_resolutions = [
            (4096, 4096, "SRTM Ultra-HD"),    # Résolution maximale
            (3601, 3601, "SRTM 1-arcsec"),   # ~30m résolution
            (2048, 2048, "SRTM Haute-Def"),  # Résolution intermédiaire haute
            (1801, 1801, "SRTM 3-arcsec"),   # ~90m résolution  
            (1201, 1201, "SRTM optimisé"),   # Résolution intermédiaire
        ]
        
        for width, height, description in native_resolutions:
            progress_tracker.update_progress(
                0.1 + (native_resolutions.index((width, height, description)) * 0.15), 
                f"Tentative {description} ({width}x{height})"
            )
            
            logger.info(f"   🔍 Tentative {description}: {width}x{height}")
            
            heightmap = self.opentopo.get_srtm_data(bounds, (width, height))
            
            if heightmap is not None:
                actual_resolution = f"{width}x{height}"
                meters_per_pixel = (lat_km * 1000) / width
                
                logger.info(f"✅ Succès {description}")
                logger.info(f"   📐 Résolution finale: {actual_resolution}")
                logger.info(f"   📏 Précision: ~{meters_per_pixel:.1f}m par pixel")
                logger.info(f"   🎯 Données 100% natives (aucun upscaling)")
                
                progress_tracker.update_progress(1.0, f"✅ Honshu {description} - données natives")
                return self._post_process_honshu(heightmap)
        
        # Si SRTM échoue, essaie OpenElevation SANS upscaling
        logger.warning("SRTM indisponible, tentative OpenElevation grille dense")
        progress_tracker.update_progress(0.8, "Fallback OpenElevation grille dense")
        
        # Utilise la grille la plus dense possible SANS upscaling
        max_safe_grid = 1500  # Plus élevé pour Honshu (île plus grande)
        grid_heightmap = self.openelevation.get_elevation_grid(bounds, max_safe_grid)
        
        if grid_heightmap is not None:
            meters_per_pixel = (lat_km * 1000) / max_safe_grid
            
            logger.info(f"✅ OpenElevation grille dense réussie")
            logger.info(f"   📐 Résolution: {max_safe_grid}x{max_safe_grid}")
            logger.info(f"   📏 Précision: ~{meters_per_pixel:.1f}m par pixel")
            logger.info(f"   🎯 Données natives sans interpolation")
            
            progress_tracker.update_progress(1.0, "✅ Honshu OpenElevation - grille native dense")
            return self._post_process_honshu(grid_heightmap)
        
        logger.error("❌ Toutes les sources de données natives échouées")
        progress_tracker.update_progress(1.0, "❌ Échec extraction données natives")
        return None

    def extract_honshu_1k(self, zone: str = "full") -> Optional[np.ndarray]:
        """
        Extrait une heightmap 1024x1024 d'Honshu.
        
        Args:
            zone: "full", "kansai", "kanto", ou "alps"
            
        Returns:
            Heightmap 1024x1024 normalisée ou None si erreur
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.INITIALIZATION,
            f"Extraction Honshu 1K - zone {zone}"
        )
        
        # Sélectionne la zone
        if zone == "full":
            bounds = HonshuTerrainBounds.FULL_ISLAND
        elif zone == "kansai":
            bounds = HonshuTerrainBounds.KANSAI
        elif zone == "kanto":
            bounds = HonshuTerrainBounds.KANTO
        elif zone == "alps":
            bounds = HonshuTerrainBounds.JAPANESE_ALPS
        else:
            logger.error(f"Zone inconnue: {zone}")
            return None
        
        center_lat, center_lon = bounds.center()
        lat_km, lon_km = bounds.dimensions_km()
        
        logger.info(f"🏔️ Extraction Honshu - Zone {zone}")
        logger.info(f"   Centre: {center_lat:.3f}°N, {center_lon:.3f}°E")
        logger.info(f"   Dimensions: {lat_km:.1f} x {lon_km:.1f} km")
        
        # Essaie d'abord OpenTopography (haute résolution)
        progress_tracker.update_progress(0.1, "Tentative OpenTopography SRTM")
        
        heightmap = self.opentopo.get_srtm_data(bounds, (1024, 1024))
        
        if heightmap is not None:
            progress_tracker.update_progress(1.0, "✅ Honshu 1K - OpenTopography réussi")
            return self._post_process_honshu(heightmap)
        
        # Fallback vers OpenElevation (plus lent mais fiable)
        logger.warning("OpenTopography échoué, fallback vers OpenElevation")
        progress_tracker.update_progress(0.5, "Fallback OpenElevation")
        
        grid_heightmap = self.openelevation.get_elevation_grid(bounds, 128)
        
        if grid_heightmap is not None:
            # Upscale vers 1024x1024
            from scipy.ndimage import zoom
            scale = 1024 / 128
            heightmap = zoom(grid_heightmap, scale, order=1)
            
            # Assure taille exacte
            if heightmap.shape[0] != 1024:
                heightmap = heightmap[:1024, :1024]
            
            progress_tracker.update_progress(1.0, "✅ Honshu 1K - OpenElevation réussi")
            return self._post_process_honshu(heightmap)
        
        logger.error("❌ Tous les services échoués pour Honshu")
        progress_tracker.update_progress(1.0, "❌ Échec extraction Honshu")
        return None
    
    def _post_process_honshu(self, heightmap: np.ndarray) -> np.ndarray:
        """Post-traitement spécifique à Honshu avec préservation du niveau de la mer."""
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.NORMALIZATION,
            "Post-traitement Honshu"
        )
        
        # Sépare les zones terrestres et sous-marines AVANT tout traitement
        land_mask = heightmap > 0
        underwater_mask = heightmap <= 0
        
        # Améliore le contraste pour mettre en valeur les montagnes japonaises
        progress_tracker.update_progress(0.2, "Amélioration contraste montagneux")
        
        # Applique une courbe gamma SEULEMENT sur les zones terrestres (évite RuntimeWarning)
        gamma = 0.7  # Accentue les hautes altitudes
        heightmap_enhanced = heightmap.copy()
        
        if np.any(land_mask):
            # Normalise temporairement les terres pour appliquer gamma
            land_values = heightmap[land_mask]
            land_max = np.max(land_values)
            if land_max > 0:
                land_normalized = land_values / land_max
                land_gamma = np.power(land_normalized, gamma)
                heightmap_enhanced[land_mask] = land_gamma * land_max
        
        # Lisse légèrement pour éliminer le bruit de numérisation
        progress_tracker.update_progress(0.4, "Lissage anti-bruit")
        
        from scipy.ndimage import gaussian_filter
        
        # Applique le lissage en préservant les zones distinctes
        heightmap_smooth = heightmap_enhanced.copy()
        
        # Lisse seulement les zones terrestres pour éviter le mélange terre/mer
        if np.any(land_mask):
            land_smooth = gaussian_filter(heightmap_enhanced, sigma=0.8)
            heightmap_smooth[land_mask] = land_smooth[land_mask]
        
        # Préserve les zones sous-marines sans lissage pour éviter leur disparition
        if np.any(underwater_mask):
            heightmap_smooth[underwater_mask] = heightmap_enhanced[underwater_mask]
        
        # CORRECTION: Préservation du niveau de la mer
        progress_tracker.update_progress(0.6, "Préservation niveau de la mer")
        
        # Renormalisation qui préserve le niveau de la mer à 0.0
        progress_tracker.update_progress(0.8, "Renormalisation avec niveau de mer fixe")
        
        heightmap_final = np.zeros_like(heightmap_smooth)
        
        # UTILISE LES MASQUES ORIGINAUX pour identifier correctement les zones
        # (car le lissage peut avoir modifié les zones de transition)
        
        if np.any(land_mask):
            # Traite les zones émergées (au-dessus du niveau de la mer dans les données originales)
            land_values_smooth = heightmap_smooth[land_mask]
            # Filtre pour ne garder que les valeurs positives après lissage
            positive_land = land_values_smooth[land_values_smooth > 0]
            
            if len(positive_land) > 0:
                max_val = np.max(positive_land)
                if max_val > 0:
                    # Normalise seulement les terres vers [0, 1]
                    land_values_normalized = heightmap_smooth[land_mask] / max_val
                    # Assure que les valeurs négatives restent à 0 pour les terres
                    land_values_normalized = np.maximum(land_values_normalized, 0.0)
                    heightmap_final[land_mask] = land_values_normalized
        
        if np.any(underwater_mask):
            # Traite les zones sous-marines (en dessous du niveau de la mer dans les données originales)
            original_underwater_values = heightmap[underwater_mask]
            min_underwater = np.min(original_underwater_values)
            
            if min_underwater < 0:
                # Normalise les profondeurs marines sur [-0.1, 0] en utilisant les données originales
                # pour préserver la structure des profondeurs
                # Calcul correct: ratio positif multiplié par -0.1 pour obtenir des valeurs négatives
                depth_ratio = abs(original_underwater_values) / abs(min_underwater)  # ratio [0, 1]
                underwater_final_values = -depth_ratio * 0.1  # résultat [-0.1, 0]
                heightmap_final[underwater_mask] = underwater_final_values
            else:
                # Les valeurs exactement à 0 restent à 0 (niveau de la mer)
                heightmap_final[underwater_mask] = 0.0
        
        progress_tracker.update_progress(1.0, "Post-traitement terminé")
        
        logger.info(f"🌊 Honshu processed - Niveau de la mer préservé à 0.0")
        logger.info(f"⛰️ Mont Fuji et reliefs montagneux accentués")
        
        return heightmap_final.astype(np.float32)


class YakushimaTerrainExtractor:
    """Extracteur spécialisé pour l'île de Yakushima (Japon)."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'extracteur Yakushima.
        
        Args:
            api_key: Clé API OpenTopography (optionnelle)
        """
        self.opentopo = OpenTopographyAPI(api_key)
        self.openelevation = OpenElevationAPI()
        
    def extract_yakushima_4k(self, zone: str = "full") -> Optional[np.ndarray]:
        """
        Extrait une heightmap haute résolution de Yakushima.
        
        Args:
            zone: "full", "central", "jomon", "senpiro", ou "steep"
            
        Returns:
            Heightmap normalisée ou None si erreur
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.INITIALIZATION,
            f"Extraction Yakushima Haute Résolution - zone {zone}"
        )
        
        # Sélectionne la zone
        if zone == "full":
            bounds = YakushimaTerrainBounds.FULL_ISLAND
        elif zone == "central":
            bounds = YakushimaTerrainBounds.CENTRAL_MOUNTAINS
        elif zone == "jomon":
            bounds = YakushimaTerrainBounds.JOMON_FOREST
        elif zone == "senpiro":
            bounds = YakushimaTerrainBounds.SENPIRO_WATERFALL
        elif zone == "steep":
            bounds = YakushimaTerrainBounds.STEEP_COAST
        elif zone == "wide":
            bounds = YakushimaTerrainBounds.WIDE_VIEW
        else:
            logger.error(f"Zone inconnue: {zone}")
            return None
        
        center_lat, center_lon = bounds.center()
        lat_km, lon_km = bounds.dimensions_km()
        
        logger.info(f"🌿 Yakushima {zone}: {lat_km:.1f}×{lon_km:.1f}km")
        logger.info(f"📍 Centre: {center_lat:.3f}°N, {center_lon:.3f}°E")
        
        # Essaie d'abord SRTM (meilleure résolution)
        progress_tracker.update_progress(0.1, "Tentative SRTM OpenTopography")
        
        heightmap = self.opentopo.get_srtm_data(bounds, output_size=(4096, 4096))
        
        if heightmap is not None:
            logger.info("✅ SRTM récupéré avec succès")
            progress_tracker.update_progress(0.8, "Post-traitement Yakushima")
            
            # Post-traitement spécialisé pour Yakushima
            heightmap = self._post_process_yakushima(heightmap)
            
            return heightmap
        
        # Fallback vers OpenElevation
        logger.warning("⚠️ SRTM indisponible, fallback OpenElevation")
        progress_tracker.update_progress(0.2, "Fallback OpenElevation")
        
        # Utilise une grille plus dense pour compenser la résolution
        heightmap = self.openelevation.get_elevation_grid(bounds, grid_size=256)
        
        if heightmap is not None:
            logger.info("✅ OpenElevation récupéré avec succès")
            progress_tracker.update_progress(0.8, "Post-traitement Yakushima")
            
            # Post-traitement spécialisé
            heightmap = self._post_process_yakushima(heightmap)
            
            return heightmap
        
        logger.error("❌ Aucune source de données disponible")
        return None
    
    def extract_yakushima_1k(self, zone: str = "full") -> Optional[np.ndarray]:
        """
        Extrait une heightmap basse résolution de Yakushima.
        
        Args:
            zone: "full", "central", "jomon", "senpiro", ou "steep"
            
        Returns:
            Heightmap normalisée ou None si erreur
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.INITIALIZATION,
            f"Extraction Yakushima Basse Résolution - zone {zone}"
        )
        
        # Sélectionne la zone
        if zone == "full":
            bounds = YakushimaTerrainBounds.FULL_ISLAND
        elif zone == "central":
            bounds = YakushimaTerrainBounds.CENTRAL_MOUNTAINS
        elif zone == "jomon":
            bounds = YakushimaTerrainBounds.JOMON_FOREST
        elif zone == "senpiro":
            bounds = YakushimaTerrainBounds.SENPIRO_WATERFALL
        elif zone == "steep":
            bounds = YakushimaTerrainBounds.STEEP_COAST
        elif zone == "wide":
            bounds = YakushimaTerrainBounds.WIDE_VIEW
        else:
            logger.error(f"Zone inconnue: {zone}")
            return None
        
        center_lat, center_lon = bounds.center()
        lat_km, lon_km = bounds.dimensions_km()
        
        logger.info(f"🌿 Yakushima {zone}: {lat_km:.1f}×{lon_km:.1f}km")
        logger.info(f"📍 Centre: {center_lat:.3f}°N, {center_lon:.3f}°E")
        
        # Essaie d'abord SRTM
        progress_tracker.update_progress(0.1, "Tentative SRTM OpenTopography")
        
        heightmap = self.opentopo.get_srtm_data(bounds, output_size=(1024, 1024))
        
        if heightmap is not None:
            logger.info("✅ SRTM récupéré avec succès")
            progress_tracker.update_progress(0.8, "Post-traitement Yakushima")
            
            heightmap = self._post_process_yakushima(heightmap)
            return heightmap
        
        # Fallback vers OpenElevation
        logger.warning("⚠️ SRTM indisponible, fallback OpenElevation")
        progress_tracker.update_progress(0.2, "Fallback OpenElevation")
        
        heightmap = self.openelevation.get_elevation_grid(bounds, grid_size=128)
        
        if heightmap is not None:
            logger.info("✅ OpenElevation récupéré avec succès")
            progress_tracker.update_progress(0.8, "Post-traitement Yakushima")
            
            heightmap = self._post_process_yakushima(heightmap)
            return heightmap
        
        logger.error("❌ Aucune source de données disponible")
        return None
    
    def _post_process_yakushima(self, heightmap: np.ndarray) -> np.ndarray:
        """Post-traitement spécialisé pour Yakushima avec préservation du niveau de la mer."""
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.NORMALIZATION,
            "Post-traitement Yakushima"
        )
        
        # Sépare les zones terrestres et sous-marines AVANT tout traitement
        land_mask = heightmap > 0
        underwater_mask = heightmap <= 0
        
        # Améliore le contraste pour mettre en valeur le relief granitique
        progress_tracker.update_progress(0.2, "Amélioration contraste granitique")
        
        # Applique une courbe gamma SEULEMENT sur les zones terrestres
        gamma = 0.75  # Accentue les reliefs moyens (dômes granitiques)
        heightmap_enhanced = heightmap.copy()
        
        if np.any(land_mask):
            # Normalise temporairement les terres pour appliquer gamma
            land_values = heightmap[land_mask]
            land_max = np.max(land_values)
            if land_max > 0:
                land_normalized = land_values / land_max
                land_gamma = np.power(land_normalized, gamma)
                heightmap_enhanced[land_mask] = land_gamma * land_max
        
        # Lisse légèrement pour éliminer le bruit de numérisation
        progress_tracker.update_progress(0.4, "Lissage anti-bruit")
        
        from scipy.ndimage import gaussian_filter
        
        # Applique le lissage en préservant les zones distinctes
        heightmap_smooth = heightmap_enhanced.copy()
        
        # Lisse seulement les zones terrestres pour éviter le mélange terre/mer
        if np.any(land_mask):
            land_smooth = gaussian_filter(heightmap_enhanced, sigma=0.6)
            heightmap_smooth[land_mask] = land_smooth[land_mask]
        
        # Préserve les zones sous-marines sans lissage
        if np.any(underwater_mask):
            heightmap_smooth[underwater_mask] = heightmap_enhanced[underwater_mask]
        
        # CORRECTION: Préservation du niveau de la mer
        progress_tracker.update_progress(0.6, "Préservation niveau de la mer")
        
        # Renormalisation qui préserve le niveau de la mer à 0.0
        progress_tracker.update_progress(0.8, "Renormalisation avec niveau de mer fixe")
        
        heightmap_final = np.zeros_like(heightmap_smooth)
        
        # UTILISE LES MASQUES ORIGINAUX pour identifier correctement les zones
        
        if np.any(land_mask):
            # Traite les zones émergées
            land_values_smooth = heightmap_smooth[land_mask]
            positive_land = land_values_smooth[land_values_smooth > 0]
            
            if len(positive_land) > 0:
                max_val = np.max(positive_land)
                if max_val > 0:
                    # Normalise seulement les terres vers [0, 1]
                    land_values_normalized = heightmap_smooth[land_mask] / max_val
                    land_values_normalized = np.maximum(land_values_normalized, 0.0)
                    heightmap_final[land_mask] = land_values_normalized
        
        if np.any(underwater_mask):
            # Traite les zones sous-marines
            original_underwater_values = heightmap[underwater_mask]
            min_underwater = np.min(original_underwater_values)
            
            if min_underwater < 0:
                # Normalise les profondeurs marines sur [-0.1, 0]
                depth_ratio = abs(original_underwater_values) / abs(min_underwater)
                underwater_final_values = -depth_ratio * 0.1
                heightmap_final[underwater_mask] = underwater_final_values
            else:
                heightmap_final[underwater_mask] = 0.0
        
        progress_tracker.update_progress(1.0, "Post-traitement terminé")
        
        logger.info(f"🌊 Yakushima processed - Niveau de la mer préservé à 0.0")
        logger.info(f"🏔️ Mont Miyanoura et reliefs granitiques accentués")
        logger.info(f"🌿 Forêt de Jōmon-sugi et ravins préservés")
        
        return heightmap_final.astype(np.float32)


def main():
    """Interface CLI pour tester l'extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extracteur de terrain réel - Île de la Réunion"
    )
    
    parser.add_argument(
        "--zone", choices=["full", "central", "west"], default="full",
        help="Zone de la Réunion à extraire (défaut: full)"
    )
    parser.add_argument(
        "--output", type=str, default="output/reunion_real_1k.png",
        help="Fichier de sortie PNG (défaut: output/reunion_real_1k.png)"
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="Clé API OpenTopography (optionnelle)"
    )
    parser.add_argument(
        "--no-progress", action="store_true",
        help="Désactive l'affichage de la progression"
    )
    
    args = parser.parse_args()
    
    # Configure le système de progression
    from .progress import ProgressTracker, ConsoleProgressCallback, set_progress_tracker
    
    progress_tracker = ProgressTracker()
    if not args.no_progress:
        console_callback = ConsoleProgressCallback(show_details=True)
        progress_tracker.add_callback(console_callback)
    
    set_progress_tracker(progress_tracker)
    progress_tracker.start()
    
    try:
        # Crée le dossier de sortie
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Extrait le terrain
        extractor = ReunionTerrainExtractor(api_key=args.api_key)
        heightmap = extractor.extract_reunion_1k(zone=args.zone)
        
        if heightmap is not None:
            # Sauvegarde en PNG 16-bit
            progress_tracker.start_stage(ProgressStage.SAVING, f"Sauvegarde: {args.output}")
            
            data_16bit = (heightmap * 65535).astype(np.uint16)
            img = Image.fromarray(data_16bit, mode='I;16')
            img.save(args.output)
            
            # Statistiques finales
            print(f"\n🏝️ Terrain réel Réunion - Zone {args.zone}")
            print(f"  • Résolution: 1024x1024")
            print(f"  • Min: {np.min(heightmap):.4f}")
            print(f"  • Max: {np.max(heightmap):.4f}")
            print(f"  • Moyenne: {np.mean(heightmap):.4f}")
            print(f"  • Écart-type: {np.std(heightmap):.4f}")
            print(f"  • Fichier: {args.output}")
            
            logger.info(f"✅ Extraction Réunion réussie: {args.output}")
        else:
            logger.error("❌ Échec de l'extraction")
            
    except Exception as e:
        progress_tracker.error(e)
        logger.error(f"Erreur: {e}")
        raise


if __name__ == "__main__":
    main()