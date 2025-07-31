"""
Module de correction des "voids" (pixels manquants) dans les données SRTM.

Ce module implémente plusieurs stratégies pour corriger les pixels manquants
dans les données d'élévation SRTM avant conversion en PNG 16-bit.

Stratégies disponibles :
1. Interpolation bilinéaire locale
2. Interpolation par splines
3. Remplissage par moyenne locale
4. Extrapolation depuis les données valides
5. Fusion multi-sources (SRTM + autres datasets)
"""

import numpy as np
from scipy import interpolate
from scipy.ndimage import binary_dilation, binary_erosion
from scipy.spatial import cKDTree
import logging
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VoidCorrectionMethod(Enum):
    """Méthodes de correction des voids disponibles."""
    BILINEAR_INTERPOLATION = "bilinear"
    SPLINE_INTERPOLATION = "spline"
    LOCAL_MEAN = "local_mean"
    EXTRAPOLATION = "extrapolation"
    MULTI_SOURCE_FUSION = "multi_source"
    ADVANCED_INPAINTING = "inpainting"


@dataclass
class VoidCorrectionConfig:
    """Configuration pour la correction des voids."""
    method: VoidCorrectionMethod = VoidCorrectionMethod.BILINEAR_INTERPOLATION
    max_void_size: int = 10  # Taille maximale des zones de voids à corriger
    interpolation_radius: int = 5  # Rayon pour l'interpolation locale
    spline_smoothing: float = 0.1  # Paramètre de lissage pour les splines
    local_mean_radius: int = 3  # Rayon pour le calcul de la moyenne locale
    extrapolation_distance: int = 20  # Distance maximale pour l'extrapolation
    min_valid_pixels: int = 4  # Nombre minimum de pixels valides pour interpolation
    preserve_coastlines: bool = True  # Préserver les côtes lors de la correction
    debug_mode: bool = False  # Mode debug avec visualisation


class VoidDetector:
    """Détecteur de voids dans les données d'élévation."""
    
    def __init__(self, nodata_value: Optional[float] = None):
        self.nodata_value = nodata_value
    
    def detect_voids(self, elevation_data: np.ndarray) -> Dict[str, Any]:
        """
        Détecte les voids dans les données d'élévation.
        
        Args:
            elevation_data: Données d'élévation 2D
            
        Returns:
            Dictionnaire avec informations sur les voids détectés
        """
        # Masque des pixels valides
        if self.nodata_value is not None:
            valid_mask = elevation_data != self.nodata_value
        else:
            # Détection automatique des valeurs aberrantes
            valid_mask = np.isfinite(elevation_data)
        
        void_mask = ~valid_mask
        
        # Statistiques des voids
        total_pixels = elevation_data.size
        void_pixels = np.sum(void_mask)
        void_percentage = (void_pixels / total_pixels) * 100
        
        # Analyse des zones de voids
        void_regions = self._analyze_void_regions(void_mask)
        
        return {
            'void_mask': void_mask,
            'valid_mask': valid_mask,
            'total_pixels': total_pixels,
            'void_pixels': void_pixels,
            'void_percentage': void_percentage,
            'void_regions': void_regions,
            'has_voids': void_pixels > 0
        }
    
    def _analyze_void_regions(self, void_mask: np.ndarray) -> Dict[str, Any]:
        """Analyse les régions de voids pour déterminer la stratégie de correction."""
        from scipy import ndimage
        
        # Étiquette les régions connectées de voids
        labeled_voids, num_regions = ndimage.label(void_mask)
        
        region_stats = []
        for i in range(1, num_regions + 1):
            region_mask = labeled_voids == i
            region_size = np.sum(region_mask)
            
            # Trouve le centre de la région
            y_coords, x_coords = np.where(region_mask)
            center_y = np.mean(y_coords)
            center_x = np.mean(x_coords)
            
            # Calcule la distance au bord le plus proche
            distance_to_edge = min(
                center_y, center_x,
                void_mask.shape[0] - center_y,
                void_mask.shape[1] - center_x
            )
            
            region_stats.append({
                'id': i,
                'size': region_size,
                'center': (center_y, center_x),
                'distance_to_edge': distance_to_edge,
                'is_small': region_size <= 10,
                'is_medium': 10 < region_size <= 100,
                'is_large': region_size > 100
            })
        
        return {
            'num_regions': num_regions,
            'regions': region_stats,
            'max_region_size': max([r['size'] for r in region_stats]) if region_stats else 0,
            'small_regions': sum(1 for r in region_stats if r['is_small']),
            'medium_regions': sum(1 for r in region_stats if r['is_medium']),
            'large_regions': sum(1 for r in region_stats if r['is_large'])
        }


class VoidCorrector:
    """Correcteur de voids dans les données d'élévation."""
    
    def __init__(self, config: VoidCorrectionConfig):
        self.config = config
        self.detector = VoidDetector()
    
    def correct_voids(self, elevation_data: np.ndarray, 
                     nodata_value: Optional[float] = None) -> np.ndarray:
        """
        Corrige les voids dans les données d'élévation.
        
        Args:
            elevation_data: Données d'élévation 2D
            nodata_value: Valeur représentant les pixels manquants
            
        Returns:
            Données d'élévation corrigées
        """
        self.detector.nodata_value = nodata_value
        void_info = self.detector.detect_voids(elevation_data)
        
        if not void_info['has_voids']:
            logger.info("Aucun void détecté, données inchangées")
            return elevation_data
        
        logger.info(f"Voids détectés: {void_info['void_percentage']:.2f}% "
                   f"({void_info['void_pixels']} pixels)")
        
        # Applique la méthode de correction appropriée
        if self.config.method == VoidCorrectionMethod.BILINEAR_INTERPOLATION:
            return self._bilinear_interpolation(elevation_data, void_info)
        elif self.config.method == VoidCorrectionMethod.SPLINE_INTERPOLATION:
            return self._spline_interpolation(elevation_data, void_info)
        elif self.config.method == VoidCorrectionMethod.LOCAL_MEAN:
            return self._local_mean_filling(elevation_data, void_info)
        elif self.config.method == VoidCorrectionMethod.EXTRAPOLATION:
            return self._extrapolation_filling(elevation_data, void_info)
        elif self.config.method == VoidCorrectionMethod.ADVANCED_INPAINTING:
            return self._advanced_inpainting(elevation_data, void_info)
        else:
            raise ValueError(f"Méthode de correction inconnue: {self.config.method}")
    
    def _bilinear_interpolation(self, elevation_data: np.ndarray, 
                               void_info: Dict[str, Any]) -> np.ndarray:
        """Interpolation bilinéaire pour corriger les petits voids."""
        corrected_data = elevation_data.copy()
        void_mask = void_info['void_mask']
        valid_mask = void_info['valid_mask']
        
        # Trouve les coordonnées des pixels valides
        valid_y, valid_x = np.where(valid_mask)
        valid_points = np.column_stack([valid_y, valid_x])
        valid_values = elevation_data[valid_mask]
        
        # Trouve les coordonnées des pixels à corriger
        void_y, void_x = np.where(void_mask)
        void_points = np.column_stack([void_y, void_x])
        
        if len(void_points) == 0:
            return corrected_data
        
        # Crée l'interpolateur
        interpolator = interpolate.LinearNDInterpolator(
            valid_points, valid_values, fill_value=np.nan
        )
        
        # Interpole les valeurs manquantes
        interpolated_values = interpolator(void_points)
        
        # Remplace les valeurs NaN par la moyenne locale
        nan_mask = np.isnan(interpolated_values)
        if np.any(nan_mask):
            for i, is_nan in enumerate(nan_mask):
                if is_nan:
                    y, x = void_points[i]
                    local_mean = self._compute_local_mean(
                        elevation_data, valid_mask, y, x, 
                        self.config.interpolation_radius
                    )
                    interpolated_values[i] = local_mean
        
        # Applique les corrections
        corrected_data[void_y, void_x] = interpolated_values
        
        logger.info(f"Interpolation bilinéaire terminée")
        return corrected_data
    
    def _spline_interpolation(self, elevation_data: np.ndarray, 
                             void_info: Dict[str, Any]) -> np.ndarray:
        """Interpolation par splines pour corriger les voids."""
        corrected_data = elevation_data.copy()
        void_mask = void_info['void_mask']
        valid_mask = void_info['valid_mask']
        
        # Trouve les coordonnées des pixels valides
        valid_y, valid_x = np.where(valid_mask)
        valid_values = elevation_data[valid_mask]
        
        # Crée l'interpolateur par splines
        interpolator = interpolate.Rbf(
            valid_x, valid_y, valid_values,
            function='thin_plate',
            smooth=self.config.spline_smoothing
        )
        
        # Génère une grille complète
        y_grid, x_grid = np.mgrid[0:elevation_data.shape[0], 0:elevation_data.shape[1]]
        
        # Interpole sur toute la grille
        interpolated_grid = interpolator(x_grid, y_grid)
        
        # Remplace seulement les pixels manquants
        corrected_data[void_mask] = interpolated_grid[void_mask]
        
        logger.info(f"Interpolation par splines terminée")
        return corrected_data
    
    def _local_mean_filling(self, elevation_data: np.ndarray, 
                           void_info: Dict[str, Any]) -> np.ndarray:
        """Remplissage par moyenne locale."""
        corrected_data = elevation_data.copy()
        void_mask = void_info['void_mask']
        valid_mask = void_info['valid_mask']
        
        void_y, void_x = np.where(void_mask)
        
        for y, x in zip(void_y, void_x):
            local_mean = self._compute_local_mean(
                elevation_data, valid_mask, y, x, 
                self.config.local_mean_radius
            )
            corrected_data[y, x] = local_mean
        
        logger.info(f"Remplissage par moyenne locale terminé")
        return corrected_data
    
    def _extrapolation_filling(self, elevation_data: np.ndarray, 
                              void_info: Dict[str, Any]) -> np.ndarray:
        """Extrapolation depuis les données valides."""
        corrected_data = elevation_data.copy()
        void_mask = void_info['void_mask']
        valid_mask = void_info['valid_mask']
        
        # Trouve les coordonnées des pixels valides
        valid_y, valid_x = np.where(valid_mask)
        valid_points = np.column_stack([valid_y, valid_x])
        valid_values = elevation_data[valid_mask]
        
        # Trouve les coordonnées des pixels à corriger
        void_y, void_x = np.where(void_mask)
        void_points = np.column_stack([void_y, void_x])
        
        if len(void_points) == 0:
            return corrected_data
        
        # Crée un arbre KD pour la recherche de voisins
        tree = cKDTree(valid_points)
        
        # Pour chaque pixel manquant, trouve le voisin le plus proche
        for i, (y, x) in enumerate(void_points):
            # Trouve les k voisins les plus proches
            distances, indices = tree.query([y, x], k=min(4, len(valid_points)))
            
            if len(indices) > 0:
                # Calcule la moyenne pondérée par la distance
                weights = 1.0 / (distances + 1e-6)  # Évite la division par zéro
                weighted_mean = np.average(valid_values[indices], weights=weights)
                corrected_data[y, x] = weighted_mean
        
        logger.info(f"Extrapolation terminée")
        return corrected_data
    
    def _advanced_inpainting(self, elevation_data: np.ndarray, 
                            void_info: Dict[str, Any]) -> np.ndarray:
        """Inpainting avancé pour corriger les voids."""
        try:
            from skimage import restoration
            corrected_data = elevation_data.copy()
            void_mask = void_info['void_mask']
            
            # Utilise l'inpainting de scikit-image
            corrected_data = restoration.inpaint.inpaint_biharmonic(
                corrected_data, void_mask
            )
            
            logger.info(f"Inpainting avancé terminé")
            return corrected_data
            
        except ImportError:
            logger.warning("scikit-image non disponible, fallback vers interpolation bilinéaire")
            return self._bilinear_interpolation(elevation_data, void_info)
    
    def _compute_local_mean(self, elevation_data: np.ndarray, 
                           valid_mask: np.ndarray, y: int, x: int, 
                           radius: int) -> float:
        """Calcule la moyenne locale des pixels valides."""
        y_min = max(0, y - radius)
        y_max = min(elevation_data.shape[0], y + radius + 1)
        x_min = max(0, x - radius)
        x_max = min(elevation_data.shape[1], x + radius + 1)
        
        local_region = elevation_data[y_min:y_max, x_min:x_max]
        local_valid = valid_mask[y_min:y_max, x_min:x_max]
        
        if np.any(local_valid):
            return np.mean(local_region[local_valid])
        else:
            # Si aucun pixel valide dans la région locale, utilise la moyenne globale
            return np.mean(elevation_data[valid_mask])


def correct_srtm_voids(elevation_data: np.ndarray, 
                      method: VoidCorrectionMethod = VoidCorrectionMethod.BILINEAR_INTERPOLATION,
                      nodata_value: Optional[float] = None,
                      **kwargs) -> np.ndarray:
    """
    Fonction utilitaire pour corriger les voids dans les données SRTM.
    
    Args:
        elevation_data: Données d'élévation SRTM
        method: Méthode de correction à utiliser
        nodata_value: Valeur représentant les pixels manquants
        **kwargs: Paramètres additionnels pour la configuration
        
    Returns:
        Données d'élévation corrigées
    """
    config = VoidCorrectionConfig(method=method, **kwargs)
    corrector = VoidCorrector(config)
    return corrector.correct_voids(elevation_data, nodata_value)


def analyze_voids(elevation_data: np.ndarray, 
                 nodata_value: Optional[float] = None) -> Dict[str, Any]:
    """
    Analyse les voids dans les données d'élévation.
    
    Args:
        elevation_data: Données d'élévation
        nodata_value: Valeur représentant les pixels manquants
        
    Returns:
        Informations détaillées sur les voids détectés
    """
    detector = VoidDetector(nodata_value)
    return detector.detect_voids(elevation_data) 