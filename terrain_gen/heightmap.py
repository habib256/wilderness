"""
Générateur de heightmap par Diamond-Square et Perlin fBm.

Ce module implémente:
1. Algorithme Diamond-Square pour la structure de base
2. Enhancement par Perlin fBm pour les détails
3. Export PNG 16-bit et données raw
4. Génération déterministe par seed
5. Suivi de progression en temps réel
"""

import argparse
import numpy as np
from typing import Tuple, Optional
from PIL import Image
import logging
from pathlib import Path
from .progress import (
    ProgressTracker, ConsoleProgressCallback, ProgressStage, 
    get_progress_tracker, set_progress_tracker
)

try:
    import fastnoise_lite as fnl
except ImportError:
    print("fastnoise_lite non disponible, utilisation de l'implémentation de base")
    fnl = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiamondSquare:
    """Implémentation optimisée de l'algorithme Diamond-Square."""
    
    def __init__(self, size: int, seed: int = 42, roughness: float = 0.5):
        """
        Initialise le générateur Diamond-Square.
        
        Args:
            size: Taille de la heightmap (doit être 2^n + 1)
            seed: Graine pour la génération déterministe
            roughness: Coefficient de rugosité (0.0 = lisse, 1.0 = très rugueux)
        """
        if not self._is_power_of_two_plus_one(size):
            # Trouve la taille valide la plus proche
            size = self._next_power_of_two_plus_one(size)
            logger.warning(f"Taille ajustée à {size} (doit être 2^n + 1)")
            
        self.size = size
        self.seed = seed
        self.roughness = roughness
        self.heightmap = np.zeros((size, size), dtype=np.float32)
        
        # Initialise le RNG
        self.rng = np.random.RandomState(seed)
        
    @staticmethod
    def _is_power_of_two_plus_one(n: int) -> bool:
        """Vérifie si n est de la forme 2^k + 1."""
        return n > 0 and (n - 1) & (n - 2) == 0
        
    @staticmethod
    def _next_power_of_two_plus_one(n: int) -> int:
        """Trouve le prochain nombre de la forme 2^k + 1."""
        power = 1
        while power + 1 < n:
            power *= 2
        return power + 1
        
    def generate(self) -> np.ndarray:
        """
        Génère la heightmap par Diamond-Square.
        
        Returns:
            Heightmap normalisée entre 0 et 1
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.DIAMOND_SQUARE, 
            f"Génération Diamond-Square {self.size}x{self.size}"
        )
        
        logger.info(f"Génération Diamond-Square {self.size}x{self.size}, seed={self.seed}")
        
        # Initialise les coins
        self.heightmap[0, 0] = self.rng.uniform(-1, 1)
        self.heightmap[0, -1] = self.rng.uniform(-1, 1)  
        self.heightmap[-1, 0] = self.rng.uniform(-1, 1)
        self.heightmap[-1, -1] = self.rng.uniform(-1, 1)
        
        # Calcul du nombre total d'itérations pour le suivi
        total_steps = 0
        temp_step = self.size - 1
        while temp_step > 1:
            total_steps += 1
            temp_step //= 2
        
        # Itère sur les niveaux de subdivision
        step = self.size - 1
        scale = 1.0
        current_iteration = 0
        
        while step > 1:
            half_step = step // 2
            
            # Phase Diamond
            progress_tracker.update_progress(
                current_iteration / total_steps, 
                f"Diamond phase - résolution {step}x{step}",
                step_size=step,
                iteration=current_iteration
            )
            self._diamond_step(step, half_step, scale)
            
            # Phase Square  
            progress_tracker.update_progress(
                (current_iteration + 0.5) / total_steps, 
                f"Square phase - résolution {step}x{step}",
                step_size=step,
                iteration=current_iteration
            )
            self._square_step(step, half_step, scale)
            
            step = half_step
            scale *= self.roughness
            current_iteration += 1
            
        # Normalise entre 0 et 1
        progress_tracker.update_progress(0.95, "Normalisation Diamond-Square")
        self._normalize()
        
        progress_tracker.update_progress(1.0, "Diamond-Square terminé")
        logger.info("Diamond-Square terminé")
        return self.heightmap.copy()
        
    def _diamond_step(self, step: int, half_step: int, scale: float):
        """Phase Diamond: remplit les centres des carrés."""
        for y in range(half_step, self.size, step):
            for x in range(half_step, self.size, step):
                # Moyenne des 4 coins
                avg = (
                    self.heightmap[y - half_step, x - half_step] +
                    self.heightmap[y - half_step, x + half_step] +
                    self.heightmap[y + half_step, x - half_step] +
                    self.heightmap[y + half_step, x + half_step]
                ) / 4.0
                
                # Ajoute le bruit
                noise = self.rng.uniform(-scale, scale)
                self.heightmap[y, x] = avg + noise
                
    def _square_step(self, step: int, half_step: int, scale: float):
        """Phase Square: remplit les centres des diamants."""
        for y in range(0, self.size, half_step):
            for x in range((y + half_step) % step, self.size, step):
                # Collecte les voisins valides
                neighbors = []
                
                if y - half_step >= 0:
                    neighbors.append(self.heightmap[y - half_step, x])
                if y + half_step < self.size:
                    neighbors.append(self.heightmap[y + half_step, x])
                if x - half_step >= 0:
                    neighbors.append(self.heightmap[y, x - half_step])
                if x + half_step < self.size:
                    neighbors.append(self.heightmap[y, x + half_step])
                    
                if neighbors:
                    avg = sum(neighbors) / len(neighbors)
                    noise = self.rng.uniform(-scale, scale)
                    self.heightmap[y, x] = avg + noise
                    
    def _normalize(self):
        """Normalise la heightmap entre 0 et 1."""
        min_val = np.min(self.heightmap)
        max_val = np.max(self.heightmap)
        
        if max_val > min_val:
            self.heightmap = (self.heightmap - min_val) / (max_val - min_val)
        else:
            self.heightmap.fill(0.5)


class PerlinFBm:
    """Générateur de bruit Perlin Fractional Brownian Motion."""
    
    def __init__(self, seed: int = 42, octaves: int = 6, 
                 frequency: float = 0.01, gain: float = 0.5, 
                 lacunarity: float = 2.0):
        """
        Initialise le générateur Perlin fBm.
        
        Args:
            seed: Graine pour la génération déterministe
            octaves: Nombre d'octaves (détail)
            frequency: Fréquence de base
            gain: Amplitude relative des octaves (persistence)  
            lacunarity: Facteur de fréquence entre octaves
        """
        self.seed = seed
        self.octaves = octaves
        self.frequency = frequency
        self.gain = gain
        self.lacunarity = lacunarity
        
        # Utilise fastnoise_lite si disponible, sinon fallback
        if fnl:
            self.noise = fnl.FastNoiseLite(seed)
            self.noise.SetNoiseType(fnl.NoiseType_Perlin)
            self.use_fastnoise = True
        else:
            self.rng = np.random.RandomState(seed)
            self.use_fastnoise = False
            logger.warning("FastNoise non disponible, utilisation du fallback")
            
    def generate(self, size: int) -> np.ndarray:
        """
        Génère une heightmap par Perlin fBm.
        
        Args:
            size: Taille de la heightmap
            
        Returns:
            Heightmap normalisée entre 0 et 1
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.PERLIN_FBM, 
            f"Génération Perlin fBm {size}x{size}, {self.octaves} octaves"
        )
        
        logger.info(f"Génération Perlin fBm {size}x{size}, octaves={self.octaves}")
        
        heightmap = np.zeros((size, size), dtype=np.float32)
        
        if self.use_fastnoise:
            heightmap = self._generate_fastnoise(size)
        else:
            heightmap = self._generate_fallback(size)
            
        # Normalise entre 0 et 1
        progress_tracker.update_progress(0.9, "Normalisation Perlin fBm")
        min_val = np.min(heightmap)
        max_val = np.max(heightmap)
        
        if max_val > min_val:
            heightmap = (heightmap - min_val) / (max_val - min_val)
        else:
            heightmap.fill(0.5)
            
        progress_tracker.update_progress(1.0, "Perlin fBm terminé")
        logger.info("Perlin fBm terminé")
        return heightmap
        
    def _generate_fastnoise(self, size: int) -> np.ndarray:
        """Génération avec FastNoiseLite (optimisée)."""
        progress_tracker = get_progress_tracker()
        
        # Configure le fBm
        progress_tracker.update_progress(0.05, "Configuration FastNoise")
        self.noise.SetFractalType(fnl.FractalType_FBm)
        self.noise.SetFractalOctaves(self.octaves)
        self.noise.SetFractalLacunarity(self.lacunarity)
        self.noise.SetFractalGain(self.gain)
        self.noise.SetFrequency(self.frequency)
        
        heightmap = np.zeros((size, size), dtype=np.float32)
        
        total_pixels = size * size
        processed_pixels = 0
        update_interval = max(1, size // 20)  # Mise à jour 20 fois par ligne
        
        for y in range(size):
            for x in range(size):
                heightmap[y, x] = self.noise.GetNoise(x, y)
                processed_pixels += 1
                
                # Mise à jour de la progression
                if x % update_interval == 0:
                    progress = 0.1 + 0.8 * (processed_pixels / total_pixels)
                    progress_tracker.update_progress(
                        progress, 
                        f"Génération ligne {y+1}/{size}",
                        pixels_processed=processed_pixels,
                        total_pixels=total_pixels
                    )
                
        return heightmap
        
    def _generate_fallback(self, size: int) -> np.ndarray:
        """Génération fallback (plus lente mais portable)."""
        progress_tracker = get_progress_tracker()
        
        heightmap = np.zeros((size, size), dtype=np.float32)
        
        amplitude = 1.0
        frequency = self.frequency
        max_value = 0.0
        
        for octave in range(self.octaves):
            # Génère une couche de bruit simple
            progress = 0.1 + 0.8 * (octave / self.octaves)
            progress_tracker.update_progress(
                progress, 
                f"Octave {octave+1}/{self.octaves} (freq={frequency:.4f})",
                octave=octave,
                frequency=frequency,
                amplitude=amplitude
            )
            
            layer = self._simple_noise(size, frequency, octave)
            heightmap += layer * amplitude
            
            max_value += amplitude
            amplitude *= self.gain
            frequency *= self.lacunarity
            
        # Normalise par la contribution totale
        progress_tracker.update_progress(0.9, "Normalisation des octaves")
        if max_value > 0:
            heightmap /= max_value
            
        return heightmap
        
    def _simple_noise(self, size: int, frequency: float, seed_offset: int) -> np.ndarray:
        """Génère du bruit simple pour le fallback."""
        # RNG avec seed modifié pour chaque octave
        local_rng = np.random.RandomState(self.seed + seed_offset)
        
        # Génère une grille de valeurs aléatoires
        grid_size = max(4, int(size * frequency))
        grid = local_rng.uniform(-1, 1, (grid_size, grid_size))
        
        # Interpole bilinéairement pour obtenir la taille finale
        from scipy.ndimage import zoom
        scale = size / grid_size
        noise = zoom(grid, scale, order=1)
        
        # Ajuste la taille exacte si nécessaire
        if noise.shape[0] != size:
            noise = noise[:size, :size]
            
        return noise


class HeightMapGenerator:
    """Générateur principal combinant Diamond-Square et Perlin fBm."""
    
    def __init__(self, size: int = 16384, seed: int = 42):
        """
        Initialise le générateur de heightmap.
        
        Args:
            size: Taille de la heightmap de sortie
            seed: Graine pour la génération déterministe
        """
        self.size = size
        self.seed = seed
        
        # Paramètres par défaut optimisés
        self.ds_roughness = 0.6
        self.fbm_octaves = 6
        self.fbm_frequency = 0.005
        self.fbm_gain = 0.5
        self.fbm_lacunarity = 2.0
        self.blend_ratio = 0.7  # 0.7 DS + 0.3 fBm
        
    def generate(self) -> np.ndarray:
        """
        Génère la heightmap finale.
        
        Returns:
            Heightmap combinée normalisée entre 0 et 1
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(
            ProgressStage.INITIALIZATION, 
            f"Initialisation génération {self.size}x{self.size}"
        )
        
        logger.info(f"Génération heightmap complète {self.size}x{self.size}")
        
        progress_tracker.update_progress(1.0, "Initialisation terminée")
        
        # Génère Diamond-Square
        ds = DiamondSquare(
            size=self.size,
            seed=self.seed,
            roughness=self.ds_roughness
        )
        ds_heightmap = ds.generate()
        
        # Redimensionne Diamond-Square si nécessaire pour correspondre à la taille demandée
        if ds_heightmap.shape[0] != self.size:
            progress_tracker.start_stage(
                ProgressStage.BLENDING, 
                "Redimensionnement Diamond-Square"
            )
            from scipy.ndimage import zoom
            scale = self.size / ds_heightmap.shape[0]
            ds_heightmap = zoom(ds_heightmap, scale, order=1)
            
            # Assure-toi de la taille exacte
            if ds_heightmap.shape[0] != self.size:
                ds_heightmap = ds_heightmap[:self.size, :self.size]
        
        # Génère Perlin fBm
        fbm = PerlinFBm(
            seed=self.seed + 1000,  # Seed différent
            octaves=self.fbm_octaves,
            frequency=self.fbm_frequency,
            gain=self.fbm_gain,
            lacunarity=self.fbm_lacunarity
        )
        fbm_heightmap = fbm.generate(self.size)
        
        # Combine les deux méthodes
        progress_tracker.start_stage(
            ProgressStage.BLENDING, 
            f"Mélange {self.blend_ratio:.1%} DS + {1-self.blend_ratio:.1%} fBm"
        )
        progress_tracker.update_progress(0.3, "Mélange des heightmaps")
        
        heightmap = (
            self.blend_ratio * ds_heightmap + 
            (1 - self.blend_ratio) * fbm_heightmap
        )
        
        # Renormalise le résultat final
        progress_tracker.start_stage(
            ProgressStage.NORMALIZATION, 
            "Normalisation finale"
        )
        progress_tracker.update_progress(0.5, "Calcul min/max")
        
        min_val = np.min(heightmap)
        max_val = np.max(heightmap)
        
        progress_tracker.update_progress(0.8, "Application normalisation")
        if max_val > min_val:
            heightmap = (heightmap - min_val) / (max_val - min_val)
        
        progress_tracker.update_progress(1.0, "Normalisation terminée")
        progress_tracker.complete()
        
        logger.info("Génération heightmap terminée")
        return heightmap
        
    def save_png(self, heightmap: np.ndarray, filepath: str):
        """
        Sauvegarde la heightmap en PNG 16-bit.
        
        Args:
            heightmap: Heightmap à sauvegarder (0-1)
            filepath: Chemin de sortie
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(ProgressStage.SAVING, f"Sauvegarde PNG: {filepath}")
        
        
        # S'assure que la heightmap est normalisée entre 0 et 1
        min_val = np.min(heightmap)
        max_val = np.max(heightmap)
        if max_val > min_val:
            heightmap = (heightmap - min_val) / (max_val - min_val)
            
        # Convertit en 16-bit
        progress_tracker.update_progress(0.3, "Conversion 16-bit")
        data_16bit = (heightmap * 65535).astype(np.uint16)
        
        # Sauvegarde avec PIL
        progress_tracker.update_progress(0.7, "Écriture fichier")
        img = Image.fromarray(data_16bit, mode='I;16')
        img.save(filepath)
        
        progress_tracker.update_progress(1.0, "Sauvegarde terminée")
        logger.info(f"Heightmap sauvegardée: {filepath}")
        
    def save_raw(self, heightmap: np.ndarray, filepath: str):
        """
        Sauvegarde les données raw en float32.
        
        Args:
            heightmap: Heightmap à sauvegarder
            filepath: Chemin de sortie (.raw)
        """
        progress_tracker = get_progress_tracker()
        progress_tracker.start_stage(ProgressStage.SAVING, f"Sauvegarde RAW: {filepath}")
        
        progress_tracker.update_progress(0.3, "Conversion float32")
        data_float32 = heightmap.astype(np.float32)
        
        progress_tracker.update_progress(0.7, "Écriture fichier raw")
        data_float32.tofile(filepath)
        
        progress_tracker.update_progress(1.0, "Sauvegarde raw terminée")
        logger.info(f"Données raw sauvegardées: {filepath}")
        
    def configure(self, **kwargs):
        """
        Configure les paramètres de génération.
        
        Args:
            ds_roughness: Rugosité Diamond-Square (0.0-1.0)
            fbm_octaves: Nombre d'octaves Perlin (1-10)
            fbm_frequency: Fréquence de base (0.001-0.1)
            fbm_gain: Gain/persistence (0.1-0.9)
            fbm_lacunarity: Lacunarité (1.5-3.0)
            blend_ratio: Ratio DS vs fBm (0.0-1.0)
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"Paramètre {key} = {value}")


def main():
    """Interface en ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Générateur de heightmap Diamond-Square + Perlin fBm"
    )
    
    parser.add_argument(
        "--size", type=int, default=16384,
        help="Taille de la heightmap (défaut: 16384)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Graine de génération (défaut: 42)"
    )
    parser.add_argument(
        "--output", type=str, default="output/heightmap.png",
        help="Fichier de sortie PNG (défaut: output/heightmap.png)"
    )
    parser.add_argument(
        "--raw", type=str, default=None,
        help="Fichier de sortie raw (optionnel)"
    )
    parser.add_argument(
        "--ds-roughness", type=float, default=0.6,
        help="Rugosité Diamond-Square (défaut: 0.6)"
    )
    parser.add_argument(
        "--fbm-octaves", type=int, default=6,
        help="Octaves Perlin fBm (défaut: 6)"
    )
    parser.add_argument(
        "--fbm-frequency", type=float, default=0.005,
        help="Fréquence Perlin fBm (défaut: 0.005)"
    )
    parser.add_argument(
        "--blend-ratio", type=float, default=0.7,
        help="Ratio Diamond-Square vs fBm (défaut: 0.7)"
    )
    parser.add_argument(
        "--no-progress", action="store_true",
        help="Désactive l'affichage de la progression"
    )
    
    args = parser.parse_args()
    
    # Configure le système de progression
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
        
        # Génère la heightmap
        generator = HeightMapGenerator(size=args.size, seed=args.seed)
        generator.configure(
            ds_roughness=args.ds_roughness,
            fbm_octaves=args.fbm_octaves,
            fbm_frequency=args.fbm_frequency,
            blend_ratio=args.blend_ratio
        )
        
        heightmap = generator.generate()
        
        # Sauvegarde
        generator.save_png(heightmap, args.output)
        
        if args.raw:
            raw_path = Path(args.raw)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            generator.save_raw(heightmap, args.raw)
        
        # Affichage final de statistiques
        if not args.no_progress:
            print(f"\n📊 Statistiques finales:")
            print(f"  • Taille: {args.size}x{args.size}")
            print(f"  • Min: {np.min(heightmap):.4f}")
            print(f"  • Max: {np.max(heightmap):.4f}")
            print(f"  • Moyenne: {np.mean(heightmap):.4f}")
            print(f"  • Écart-type: {np.std(heightmap):.4f}")
            print(f"  • Fichier: {args.output}")
        
        logger.info(f"Génération terminée avec succès: {args.output}")
        
    except Exception as e:
        progress_tracker.error(e)
        logger.error(f"Erreur lors de la génération: {e}")
        raise


if __name__ == "__main__":
    main() 