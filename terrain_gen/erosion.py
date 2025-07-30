"""
Module d'érosion hydraulique GPU avec CuPy.

Implémente l'algorithme d'érosion hydraulique de base avec support GPU
pour des performances optimales sur de grandes heightmaps.
"""

import numpy as np
import logging
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import time

# Import conditionnel de CuPy
try:
    import cupy as cp
    # Test si CUDA est vraiment disponible
    cp.cuda.Device(0).compute_capability
    CUPY_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("CuPy + CUDA disponible - Érosion GPU activée")
except (ImportError, Exception) as e:
    CUPY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"CuPy/CUDA non disponible ({e}) - Utilisation CPU")

# CuPy détecté automatiquement
logger = logging.getLogger(__name__)
if CUPY_AVAILABLE:
    logger.info("CuPy + CUDA disponible - Érosion GPU activée")
else:
    logger.info("CuPy non disponible - Utilisation CPU")

from .progress import ProgressTracker, ProgressStage, get_progress_tracker


class HydraulicErosion:
    """
    Algorithme d'érosion hydraulique GPU optimisé.
    
    Basé sur l'algorithme de base de l'érosion hydraulique :
    1. Génération de gouttes d'eau aléatoires
    2. Simulation du chemin de descente
    3. Transport et dépôt de sédiments
    4. Modification de la heightmap
    """
    
    def __init__(self, 
                 iterations: int = 50000,
                 erosion_radius: float = 3.0,
                 inertia: float = 0.05,
                 sediment_capacity_factor: float = 4.0,
                 min_slope: float = 0.01,
                 gravity: float = 4.0,
                 evaporation_speed: float = 0.01,
                 deposition_speed: float = 0.1,
                 erosion_speed: float = 0.3,
                 seed: int = 42):
        """
        Initialise les paramètres d'érosion.
        
        Args:
            iterations: Nombre de gouttes d'eau à simuler
            erosion_radius: Rayon d'érosion autour de chaque goutte
            inertia: Inertie de la goutte (0-1)
            sediment_capacity_factor: Facteur de capacité de transport
            min_slope: Pente minimale pour l'érosion
            gravity: Force de gravité
            evaporation_speed: Vitesse d'évaporation
            deposition_speed: Vitesse de dépôt
            erosion_speed: Vitesse d'érosion
            seed: Seed pour la génération aléatoire
        """
        self.iterations = iterations
        self.erosion_radius = erosion_radius
        self.inertia = inertia
        self.sediment_capacity_factor = sediment_capacity_factor
        self.min_slope = min_slope
        self.gravity = gravity
        self.evaporation_speed = evaporation_speed
        self.deposition_speed = deposition_speed
        self.erosion_speed = erosion_speed
        self.seed = seed
        
        # Initialisation du générateur aléatoire (sera fait dans erode())
        self.rng = None
    
    def erode(self, heightmap: np.ndarray, 
              progress_callback: Optional[callable] = None) -> np.ndarray:
        """
        Applique l'érosion hydraulique à une heightmap.
        
        Args:
            heightmap: Heightmap d'entrée (numpy array)
            progress_callback: Callback pour le suivi de progression
            
        Returns:
            Heightmap érodée
        """
        if not CUPY_AVAILABLE:
            logger.warning("CuPy non disponible - Utilisation CPU (très lent)")
            return self._erode_cpu(heightmap, progress_callback)
        
        return self._erode_gpu(heightmap, progress_callback)
    
    def _erode_gpu(self, heightmap: np.ndarray, 
                   progress_callback: Optional[callable] = None) -> np.ndarray:
        """Version GPU de l'érosion avec CuPy."""
        
        # Initialisation du générateur aléatoire GPU
        self.rng = cp.random.RandomState(self.seed)
        
        # Transfert vers GPU
        heightmap_gpu = cp.asarray(heightmap, dtype=cp.float32)
        heightmap_original = heightmap_gpu.copy()
        
        # Paramètres
        map_size = heightmap_gpu.shape[0]
        map_size_minus_one = map_size - 1
        
        # Initialisation du tracker de progression
        progress = get_progress_tracker()
        progress.start_stage(ProgressStage.EROSION, self.iterations)
        
        logger.info(f"Début érosion GPU: {self.iterations} itérations sur {map_size}x{map_size}")
        start_time = time.time()
        
        # Boucle principale d'érosion
        for i in range(self.iterations):
            # Génération position aléatoire
            pos_x = self.rng.uniform(0, map_size_minus_one)
            pos_y = self.rng.uniform(0, map_size_minus_one)
            
            # Direction initiale aléatoire
            dir_x = 0
            dir_y = 0
            
            # État de la goutte
            speed = 1.0
            water = 1.0
            sediment = 0.0
            
            # Simulation du chemin de la goutte
            while water > 0.01 and speed > 0.01:
                # Coordonnées entières
                node_x = int(pos_x)
                node_y = int(pos_y)
                
                # Coordonnées décimales dans la cellule
                cell_offset_x = pos_x - node_x
                cell_offset_y = pos_y - node_y
                
                # Calcul de la hauteur et du gradient
                height_nw = heightmap_gpu[node_y, node_x]
                height_ne = heightmap_gpu[node_y, min(node_x + 1, map_size_minus_one)]
                height_sw = heightmap_gpu[min(node_y + 1, map_size_minus_one), node_x]
                height_se = heightmap_gpu[min(node_y + 1, map_size_minus_one), 
                                        min(node_x + 1, map_size_minus_one)]
                
                # Interpolation bilinéaire pour la hauteur
                height = (height_nw * (1 - cell_offset_x) * (1 - cell_offset_y) +
                         height_ne * cell_offset_x * (1 - cell_offset_y) +
                         height_sw * (1 - cell_offset_x) * cell_offset_y +
                         height_se * cell_offset_x * cell_offset_y)
                
                # Calcul du gradient
                gradient_x = (height_ne - height_nw) * (1 - cell_offset_y) + (height_se - height_sw) * cell_offset_y
                gradient_y = (height_sw - height_nw) * (1 - cell_offset_x) + (height_se - height_ne) * cell_offset_x
                
                # Normalisation du gradient
                length = cp.sqrt(gradient_x * gradient_x + gradient_y * gradient_y)
                if length > 0:
                    gradient_x /= length
                    gradient_y /= length
                
                # Mise à jour de la direction
                dir_x = (dir_x * self.inertia - gradient_x * (1 - self.inertia))
                dir_y = (dir_y * self.inertia - gradient_y * (1 - self.inertia))
                
                # Normalisation de la direction
                length = cp.sqrt(dir_x * dir_x + dir_y * dir_y)
                if length > 0:
                    dir_x /= length
                    dir_y /= length
                
                # Nouvelle position
                pos_x += dir_x
                pos_y += dir_y
                
                # Vérification des limites
                if pos_x < 0 or pos_x >= map_size_minus_one or pos_y < 0 or pos_y >= map_size_minus_one:
                    break
                
                # Nouvelle hauteur
                new_height = (height_nw * (1 - cell_offset_x) * (1 - cell_offset_y) +
                             height_ne * cell_offset_x * (1 - cell_offset_y) +
                             height_sw * (1 - cell_offset_x) * cell_offset_y +
                             height_se * cell_offset_x * cell_offset_y)
                
                # Calcul de la différence de hauteur
                height_diff = new_height - height
                
                # Calcul de la capacité de transport
                slope = max(self.min_slope, cp.sqrt(gradient_x * gradient_x + gradient_y * gradient_y))
                sediment_capacity = max(0.01, -height_diff) * speed * water * self.sediment_capacity_factor
                
                # Transport de sédiments
                if sediment > sediment_capacity or height_diff > 0:
                    # Dépôt
                    amount_to_deposit = (sediment - sediment_capacity) * self.deposition_speed if height_diff > 0 else self.deposition_speed
                    amount_to_deposit = min(amount_to_deposit, sediment)
                    
                    sediment -= amount_to_deposit
                    
                    # Application du dépôt (interpolation bilinéaire inverse)
                    heightmap_gpu[node_y, node_x] += amount_to_deposit * (1 - cell_offset_x) * (1 - cell_offset_y)
                    heightmap_gpu[node_y, min(node_x + 1, map_size_minus_one)] += amount_to_deposit * cell_offset_x * (1 - cell_offset_y)
                    heightmap_gpu[min(node_y + 1, map_size_minus_one), node_x] += amount_to_deposit * (1 - cell_offset_x) * cell_offset_y
                    heightmap_gpu[min(node_y + 1, map_size_minus_one), 
                                 min(node_x + 1, map_size_minus_one)] += amount_to_deposit * cell_offset_x * cell_offset_y
                else:
                    # Érosion
                    amount_to_erode = min((sediment_capacity - sediment) * self.erosion_speed, -height_diff)
                    
                    # Application de l'érosion (interpolation bilinéaire inverse)
                    heightmap_gpu[node_y, node_x] -= amount_to_erode * (1 - cell_offset_x) * (1 - cell_offset_y)
                    heightmap_gpu[node_y, min(node_x + 1, map_size_minus_one)] -= amount_to_erode * cell_offset_x * (1 - cell_offset_y)
                    heightmap_gpu[min(node_y + 1, map_size_minus_one), node_x] -= amount_to_erode * (1 - cell_offset_x) * cell_offset_y
                    heightmap_gpu[min(node_y + 1, map_size_minus_one), 
                                 min(node_x + 1, map_size_minus_one)] -= amount_to_erode * cell_offset_x * cell_offset_y
                    
                    sediment += amount_to_erode
                
                # Mise à jour de la vitesse et de l'eau
                speed = cp.sqrt(speed * speed + height_diff * self.gravity)
                water *= (1 - self.evaporation_speed)
            
            # Mise à jour de la progression
            if i % 1000 == 0:
                progress.update_progress(i / self.iterations, f"Itération {i}/{self.iterations}")
        
        # Finalisation
        progress.complete_stage(ProgressStage.EROSION)
        
        # Transfert vers CPU
        result = cp.asnumpy(heightmap_gpu)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Érosion GPU terminée en {elapsed_time:.2f}s")
        
        return result
    
    def _erode_cpu(self, heightmap: np.ndarray, 
                   progress_callback: Optional[callable] = None) -> np.ndarray:
        """Version CPU de l'érosion (fallback)."""
        logger.info("Utilisation de la version CPU de l'érosion")
        
        # Initialisation du générateur aléatoire CPU
        self.rng = np.random.RandomState(self.seed)
        
        # Copie de la heightmap
        heightmap_cpu = heightmap.copy().astype(np.float32)
        
        # Paramètres
        map_size = heightmap_cpu.shape[0]
        map_size_minus_one = map_size - 1
        
        # Initialisation du tracker de progression
        progress = get_progress_tracker()
        progress.start_stage(ProgressStage.EROSION, self.iterations)
        
        logger.info(f"Début érosion CPU: {self.iterations} itérations sur {map_size}x{map_size}")
        start_time = time.time()
        
        # Variables de debug
        total_erosion = 0.0
        total_deposition = 0.0
        
        # Boucle principale d'érosion
        for i in range(self.iterations):
            # Génération position aléatoire
            pos_x = self.rng.uniform(0, map_size_minus_one)
            pos_y = self.rng.uniform(0, map_size_minus_one)
            
            # Direction initiale aléatoire
            dir_x = 0
            dir_y = 0
            
            # État de la goutte
            speed = 1.0
            water = 1.0
            sediment = 0.0
            
            # Simulation du chemin de la goutte
            while water > 0.01 and speed > 0.01:
                # Coordonnées entières
                node_x = int(pos_x)
                node_y = int(pos_y)
                
                # Coordonnées décimales dans la cellule
                cell_offset_x = pos_x - node_x
                cell_offset_y = pos_y - node_y
                
                # Calcul de la hauteur et du gradient
                height_nw = heightmap_cpu[node_y, node_x]
                height_ne = heightmap_cpu[node_y, min(node_x + 1, map_size_minus_one)]
                height_sw = heightmap_cpu[min(node_y + 1, map_size_minus_one), node_x]
                height_se = heightmap_cpu[min(node_y + 1, map_size_minus_one), 
                                        min(node_x + 1, map_size_minus_one)]
                
                # Interpolation bilinéaire pour la hauteur
                height = (height_nw * (1 - cell_offset_x) * (1 - cell_offset_y) +
                         height_ne * cell_offset_x * (1 - cell_offset_y) +
                         height_sw * (1 - cell_offset_x) * cell_offset_y +
                         height_se * cell_offset_x * cell_offset_y)
                
                # Calcul du gradient
                gradient_x = (height_ne - height_nw) * (1 - cell_offset_y) + (height_se - height_sw) * cell_offset_y
                gradient_y = (height_sw - height_nw) * (1 - cell_offset_x) + (height_se - height_ne) * cell_offset_x
                
                # Normalisation du gradient
                gradient_length = np.sqrt(gradient_x * gradient_x + gradient_y * gradient_y)
                if gradient_length > 0:
                    gradient_x /= gradient_length
                    gradient_y /= gradient_length
                
                # Mise à jour de la direction
                dir_x = (dir_x * self.inertia - gradient_x * (1 - self.inertia))
                dir_y = (dir_y * self.inertia - gradient_y * (1 - self.inertia))
                
                # Normalisation de la direction
                length = np.sqrt(dir_x * dir_x + dir_y * dir_y)
                if length > 0:
                    dir_x /= length
                    dir_y /= length
                
                # Nouvelle position
                pos_x += dir_x
                pos_y += dir_y
                
                # Vérification des limites
                if pos_x < 0 or pos_x >= map_size_minus_one or pos_y < 0 or pos_y >= map_size_minus_one:
                    break
                
                # Nouvelle hauteur
                new_height = (height_nw * (1 - cell_offset_x) * (1 - cell_offset_y) +
                             height_ne * cell_offset_x * (1 - cell_offset_y) +
                             height_sw * (1 - cell_offset_x) * cell_offset_y +
                             height_se * cell_offset_x * cell_offset_y)
                
                # Calcul de la différence de hauteur
                height_diff = new_height - height
                
                # Calcul de la capacité de transport
                slope = max(self.min_slope, gradient_length)  # Utiliser la magnitude du gradient brut
                sediment_capacity = max(0.01, -height_diff) * speed * water * self.sediment_capacity_factor
                
                # Transport de sédiments
                if sediment > sediment_capacity or height_diff > 0:
                    # Dépôt
                    if height_diff > 0:
                        # En montée : déposer l'excès de sédiment seulement
                        amount_to_deposit = max(0, (sediment - sediment_capacity) * self.deposition_speed)
                    else:
                        # Conditions normales : déposer selon deposition_speed
                        amount_to_deposit = sediment * self.deposition_speed
                    
                    # S'assurer qu'on ne dépose pas plus que ce qu'on a
                    amount_to_deposit = max(0, min(amount_to_deposit, sediment))
                    
                    sediment -= amount_to_deposit
                    
                    # Application du dépôt (interpolation bilinéaire inverse)
                    heightmap_cpu[node_y, node_x] += amount_to_deposit * (1 - cell_offset_x) * (1 - cell_offset_y)
                    heightmap_cpu[node_y, min(node_x + 1, map_size_minus_one)] += amount_to_deposit * cell_offset_x * (1 - cell_offset_y)
                    heightmap_cpu[min(node_y + 1, map_size_minus_one), node_x] += amount_to_deposit * (1 - cell_offset_x) * cell_offset_y
                    heightmap_cpu[min(node_y + 1, map_size_minus_one), 
                                 min(node_x + 1, map_size_minus_one)] += amount_to_deposit * cell_offset_x * cell_offset_y
                    total_deposition += amount_to_deposit
                else:
                    # Érosion
                    amount_to_erode = min((sediment_capacity - sediment) * self.erosion_speed, -height_diff)
                    amount_to_erode = max(0, amount_to_erode)  # S'assurer que l'érosion est positive
                    
                    if amount_to_erode > 0:
                        # Application de l'érosion (interpolation bilinéaire inverse)
                        heightmap_cpu[node_y, node_x] -= amount_to_erode * (1 - cell_offset_x) * (1 - cell_offset_y)
                        heightmap_cpu[node_y, min(node_x + 1, map_size_minus_one)] -= amount_to_erode * cell_offset_x * (1 - cell_offset_y)
                        heightmap_cpu[min(node_y + 1, map_size_minus_one), node_x] -= amount_to_erode * (1 - cell_offset_x) * cell_offset_y
                        heightmap_cpu[min(node_y + 1, map_size_minus_one), 
                                     min(node_x + 1, map_size_minus_one)] -= amount_to_erode * cell_offset_x * cell_offset_y
                        
                        sediment += amount_to_erode
                        total_erosion += amount_to_erode
                
                # Mise à jour de la vitesse et de l'eau
                speed = np.sqrt(speed * speed + height_diff * self.gravity)
                water *= (1 - self.evaporation_speed)
            
            # Mise à jour de la progression
            if i % 1000 == 0:
                progress.update_progress(i / self.iterations, f"Itération {i}/{self.iterations}")
        
        # Finalisation
        progress.complete_stage(ProgressStage.EROSION)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Érosion CPU terminée en {elapsed_time:.2f}s")
        logger.info(f"Total érosion appliquée: {total_erosion:.6f}")
        logger.info(f"Total dépôt appliqué: {total_deposition:.6f}")
        
        return heightmap_cpu


class ErosionPipeline:
    """
    Pipeline complet d'érosion avec paramètres prédéfinis.
    """
    
    @staticmethod
    def light_erosion(heightmap: np.ndarray, 
                     progress_callback: Optional[callable] = None) -> np.ndarray:
        """Érosion légère pour terrains doux."""
        eroder = HydraulicErosion(
            iterations=10000,
            erosion_radius=2.0,
            inertia=0.05,
            sediment_capacity_factor=3.0,
            min_slope=0.01,
            gravity=3.0,
            evaporation_speed=0.01,
            deposition_speed=0.1,
            erosion_speed=0.2
        )
        return eroder.erode(heightmap, progress_callback)
    
    @staticmethod
    def medium_erosion(heightmap: np.ndarray, 
                      progress_callback: Optional[callable] = None) -> np.ndarray:
        """Érosion moyenne pour terrains équilibrés."""
        eroder = HydraulicErosion(
            iterations=30000,
            erosion_radius=3.0,
            inertia=0.05,
            sediment_capacity_factor=4.0,
            min_slope=0.01,
            gravity=4.0,
            evaporation_speed=0.01,
            deposition_speed=0.1,
            erosion_speed=0.3
        )
        return eroder.erode(heightmap, progress_callback)
    
    @staticmethod
    def heavy_erosion(heightmap: np.ndarray, 
                     progress_callback: Optional[callable] = None) -> np.ndarray:
        """Érosion forte pour terrains montagneux."""
        eroder = HydraulicErosion(
            iterations=50000,
            erosion_radius=4.0,
            inertia=0.05,
            sediment_capacity_factor=5.0,
            min_slope=0.01,
            gravity=5.0,
            evaporation_speed=0.01,
            deposition_speed=0.1,
            erosion_speed=0.4
        )
        return eroder.erode(heightmap, progress_callback)


def erode_heightmap(heightmap: np.ndarray, 
                   intensity: str = "medium",
                   progress_callback: Optional[callable] = None) -> np.ndarray:
    """
    Fonction utilitaire pour éroder une heightmap.
    
    Args:
        heightmap: Heightmap d'entrée
        intensity: "light", "medium", ou "heavy"
        progress_callback: Callback pour le suivi de progression
        
    Returns:
        Heightmap érodée
    """
    if intensity == "light":
        return ErosionPipeline.light_erosion(heightmap, progress_callback)
    elif intensity == "medium":
        return ErosionPipeline.medium_erosion(heightmap, progress_callback)
    elif intensity == "heavy":
        return ErosionPipeline.heavy_erosion(heightmap, progress_callback)
    else:
        raise ValueError(f"Intensité inconnue: {intensity}. Utilisez 'light', 'medium', ou 'heavy'")


if __name__ == "__main__":
    # Test simple
    from .heightmap import HeightMapGenerator
    
    generator = HeightMapGenerator(size=256, seed=42)
    heightmap = generator.generate()
    
    print("Génération terminée, début érosion...")
    eroded = erode_heightmap(heightmap, "medium")
    print("Érosion terminée!")
    
    # Sauvegarde
    generator.save_png(eroded, "output/eroded_heightmap.png")
    print("Sauvegardé dans output/eroded_heightmap.png")