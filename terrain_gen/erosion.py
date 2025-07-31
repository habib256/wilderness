"""
Algorithme d'érosion de terrain (hydraulique + thermique) optimisé.

Ce module implémente une simulation physique d'érosion combinant :
- Érosion hydraulique : transport de sédiments par l'eau
- Érosion thermique : glissement de terrain sur les pentes critiques
"""

import numpy as np
from numba import njit, prange
from typing import Dict, Tuple, Optional
import time


@njit(parallel=True)
def _compute_gradients(heightmap: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calcule les gradients en X et Y de la heightmap.
    
    Parameters
    ----------
    heightmap : np.ndarray
        Heightmap d'entrée de forme (H, W)
        
    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        Gradients en X et Y de même forme que heightmap
    """
    H, W = heightmap.shape
    grad_x = np.zeros_like(heightmap)
    grad_y = np.zeros_like(heightmap)
    
    for i in prange(H):
        for j in range(W):
            # Gradient en X (direction j)
            if j == 0:
                grad_x[i, j] = heightmap[i, 1] - heightmap[i, 0]
            elif j == W - 1:
                grad_x[i, j] = heightmap[i, j] - heightmap[i, j-1]
            else:
                grad_x[i, j] = (heightmap[i, j+1] - heightmap[i, j-1]) / 2.0
                
            # Gradient en Y (direction i)
            if i == 0:
                grad_y[i, j] = heightmap[1, j] - heightmap[0, j]
            elif i == H - 1:
                grad_y[i, j] = heightmap[i, j] - heightmap[i-1, j]
            else:
                grad_y[i, j] = (heightmap[i+1, j] - heightmap[i-1, j]) / 2.0
    
    return grad_x, grad_y


@njit(parallel=True)
def _hydraulic_erosion_step(
    heightmap: np.ndarray,
    water: np.ndarray,
    sediment: np.ndarray,
    rain_rate: float,
    evap_rate: float,
    sed_capacity: float,
    dissolve_rate: float,
    deposit_rate: float,
    gravity: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Effectue une étape d'érosion hydraulique.
    
    Parameters
    ----------
    heightmap : np.ndarray
        Heightmap actuelle
    water : np.ndarray
        Carte d'eau actuelle
    sediment : np.ndarray
        Carte de sédiments actuelle
    rain_rate : float
        Taux de pluie par itération
    evap_rate : float
        Taux d'évaporation
    sed_capacity : float
        Capacité de transport de sédiments
    dissolve_rate : float
        Taux de dissolution
    deposit_rate : float
        Taux de dépôt
    gravity : float
        Accélération gravitationnelle
        
    Returns
    -------
    Tuple[np.ndarray, np.ndarray, np.ndarray]
        Nouvelles heightmap, eau et sédiments
    """
    H, W = heightmap.shape
    new_heightmap = heightmap.copy()
    new_water = water.copy()
    new_sediment = sediment.copy()
    
    # Ajout de pluie
    new_water += rain_rate
    
    # Calcul des gradients
    grad_x, grad_y = _compute_gradients(heightmap)
    
    # Flux d'eau et transport de sédiments
    for i in prange(1, H-1):
        for j in range(1, W-1):
            # Direction du flux (plus forte pente)
            slope_x = grad_x[i, j]
            slope_y = grad_y[i, j]
            slope_magnitude = np.sqrt(slope_x**2 + slope_y**2)
            
            if slope_magnitude > 0:
                # Normalisation de la direction
                dir_x = -slope_x / slope_magnitude
                dir_y = -slope_y / slope_magnitude
                
                # Vitesse du flux (proportionnelle à la pente et à l'eau)
                velocity = slope_magnitude * new_water[i, j] * gravity
                
                # Capacité de transport de sédiments
                capacity = sed_capacity * velocity * slope_magnitude
                
                # Érosion/dépôt
                if new_sediment[i, j] < capacity:
                    # Érosion
                    erosion = min(
                        (capacity - new_sediment[i, j]) * dissolve_rate,
                        new_heightmap[i, j] - 0.0  # Éviter les hauteurs négatives
                    )
                    new_heightmap[i, j] -= erosion
                    new_sediment[i, j] += erosion
                else:
                    # Dépôt
                    deposit = (new_sediment[i, j] - capacity) * deposit_rate
                    new_heightmap[i, j] += deposit
                    new_sediment[i, j] -= deposit
                
                # Transport de sédiments vers les cellules voisines
                if abs(dir_x) > abs(dir_y):
                    # Flux principal en X
                    target_j = j + int(np.sign(dir_x))
                    if 0 < target_j < W:
                        transfer = new_sediment[i, j] * 0.1
                        new_sediment[i, j] -= transfer
                        new_sediment[i, target_j] += transfer
                else:
                    # Flux principal en Y
                    target_i = i + int(np.sign(dir_y))
                    if 0 < target_i < H:
                        transfer = new_sediment[i, j] * 0.1
                        new_sediment[i, j] -= transfer
                        new_sediment[target_i, j] += transfer
    
    # Évaporation
    new_water *= (1.0 - evap_rate)
    
    return new_heightmap, new_water, new_sediment


@njit(parallel=True)
def _thermal_erosion_step(
    heightmap: np.ndarray,
    thermal_angle: float,
    thermal_rate: float
) -> np.ndarray:
    """
    Effectue une étape d'érosion thermique (glissement de terrain).
    
    Parameters
    ----------
    heightmap : np.ndarray
        Heightmap actuelle
    thermal_angle : float
        Angle critique en degrés
    thermal_rate : float
        Taux d'érosion thermique
        
    Returns
    -------
    np.ndarray
        Nouvelle heightmap après érosion thermique
    """
    H, W = heightmap.shape
    new_heightmap = heightmap.copy()
    critical_slope = np.tan(np.radians(thermal_angle))
    
    for i in prange(1, H-1):
        for j in range(1, W-1):
            # Calcul de la pente maximale vers les voisins
            max_slope = 0.0
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    if di == 0 and dj == 0:
                        continue
                    
                    ni, nj = i + di, j + dj
                    if 0 <= ni < H and 0 <= nj < W:
                        slope = (heightmap[i, j] - heightmap[ni, nj]) / np.sqrt(di**2 + dj**2)
                        max_slope = max(max_slope, slope)
            
            # Si la pente dépasse l'angle critique, glissement
            if max_slope > critical_slope:
                # Trouver le voisin le plus bas
                min_height = heightmap[i, j]
                min_ni, min_nj = i, j
                
                for di in [-1, 0, 1]:
                    for dj in [-1, 0, 1]:
                        if di == 0 and dj == 0:
                            continue
                        
                        ni, nj = i + di, j + dj
                        if 0 <= ni < H and 0 <= nj < W:
                            if heightmap[ni, nj] < min_height:
                                min_height = heightmap[ni, nj]
                                min_ni, min_nj = ni, nj
                
                # Transfert de matière
                if min_ni != i or min_nj != j:
                    transfer = (heightmap[i, j] - min_height) * thermal_rate * 0.5
                    new_heightmap[i, j] -= transfer
                    new_heightmap[min_ni, min_nj] += transfer
    
    return new_heightmap


def erosion(
    heightmap: np.ndarray, 
    n_iters: int, 
    params: Dict[str, float]
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Applique l'érosion hydraulique et thermique à une heightmap.
    
    Parameters
    ----------
    heightmap : np.ndarray
        Heightmap d'entrée de forme (H, W) en mètres
    n_iters : int
        Nombre d'itérations de simulation (≥ 1)
    params : Dict[str, float]
        Paramètres de simulation :
        - rain_rate: Taux de pluie en mm par itération
        - evap_rate: Taux d'évaporation (0-1)
        - sed_capacity: Capacité de transport de sédiments en kg/m³
        - dissolve_rate: Taux de dissolution (0-1)
        - deposit_rate: Taux de dépôt (0-1)
        - thermal_angle: Angle critique en degrés
        - thermal_rate: Taux d'érosion thermique (0-1)
        - gravity: Accélération gravitationnelle (défaut: 9.81)
        - seed: Graine pour reproductibilité (optionnel)
        
    Returns
    -------
    Tuple[np.ndarray, Dict[str, float]]
        Heightmap érodée et métriques de simulation
        
    Raises
    ------
    ValueError
        Si les paramètres sont invalides
    """
    # Validation des paramètres
    if n_iters < 1:
        raise ValueError("n_iters doit être ≥ 1")
    
    if heightmap.ndim != 2:
        raise ValueError("heightmap doit être 2D")
    
    # Paramètres par défaut
    default_params = {
        "rain_rate": 0.01,
        "evap_rate": 0.1,
        "sed_capacity": 1.0,
        "dissolve_rate": 0.1,
        "deposit_rate": 0.1,
        "thermal_angle": 30.0,
        "thermal_rate": 0.1,
        "gravity": 9.81,
        "seed": None
    }
    
    # Fusion avec les paramètres par défaut
    for key, default_value in default_params.items():
        if key not in params:
            params[key] = default_value
    
    # Initialisation du générateur aléatoire si seed fourni
    if params["seed"] is not None:
        np.random.seed(params["seed"])
    
    H, W = heightmap.shape
    result = heightmap.copy().astype(np.float32)
    
    # Initialisation des cartes d'eau et de sédiments
    water = np.zeros((H, W), dtype=np.float32)
    sediment = np.zeros((H, W), dtype=np.float32)
    
    # Métriques de suivi
    initial_volume = np.sum(result)
    initial_mass = initial_volume + np.sum(sediment)
    
    start_time = time.time()
    
    # Boucle principale de simulation
    for iteration in range(n_iters):
        # Érosion hydraulique
        result, water, sediment = _hydraulic_erosion_step(
            result, water, sediment,
            params["rain_rate"], params["evap_rate"],
            params["sed_capacity"], params["dissolve_rate"],
            params["deposit_rate"], params["gravity"]
        )
        
        # Érosion thermique
        result = _thermal_erosion_step(
            result, params["thermal_angle"], params["thermal_rate"]
        )
    
    end_time = time.time()
    
    # Calcul des métriques finales
    final_volume = np.sum(result)
    final_mass = final_volume + np.sum(sediment)
    
    # Conservation de masse
    mass_conservation = abs(final_mass - initial_mass) / initial_mass * 100
    
    # Volume transporté
    volume_transported = abs(final_volume - initial_volume)
    
    # Perte numérique (devrait être proche de 0)
    numerical_loss = abs(final_mass - initial_mass)
    
    metrics = {
        "volume_transported": float(volume_transported),
        "mass_conservation_percent": float(mass_conservation),
        "numerical_loss": float(numerical_loss),
        "cpu_time_seconds": float(end_time - start_time),
        "iterations": n_iters,
        "grid_size": f"{H}x{W}"
    }
    
    return result, metrics


def demo() -> None:
    """
    Démonstration de l'algorithme d'érosion sur un terrain simple.
    """
    print("=== Démonstration Érosion Hydraulique ===")
    
    # Génération d'un terrain simple
    size = 256
    heightmap = np.random.rand(size, size).astype(np.float32)
    
    # Paramètres d'érosion
    params = {
        "rain_rate": 0.01,
        "evap_rate": 0.1,
        "sed_capacity": 1.0,
        "dissolve_rate": 0.1,
        "deposit_rate": 0.1,
        "thermal_angle": 30.0,
        "thermal_rate": 0.1,
        "gravity": 9.81,
        "seed": 42
    }
    
    print(f"Terrain initial: {size}x{size}")
    print(f"Altitude min/max: {heightmap.min():.3f}/{heightmap.max():.3f}")
    
    # Application de l'érosion
    eroded, metrics = erosion(heightmap, n_iters=50, params=params)
    
    print(f"Terrain érodé: {size}x{size}")
    print(f"Altitude min/max: {eroded.min():.3f}/{eroded.max():.3f}")
    print(f"Temps de simulation: {metrics['cpu_time_seconds']:.2f}s")
    print(f"Conservation de masse: {metrics['mass_conservation_percent']:.6f}")
    print("=== Démonstration terminée ===")


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path
    
    def main():
        parser = argparse.ArgumentParser(
            description="Algorithme d'érosion hydraulique et thermique pour heightmaps",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Exemples d'utilisation:
  # Érosion légère sur heightmap existante
  python -m terrain_gen.erosion input.png --iterations 20 --output eroded_light.png
  
  # Érosion forte avec paramètres personnalisés
  python -m terrain_gen.erosion input.png --iterations 100 --rain-rate 0.02 --thermal-rate 0.2
  
  # Érosion thermique uniquement
  python -m terrain_gen.erosion input.png --iterations 50 --rain-rate 0 --thermal-rate 0.15
  
  # Démonstration avec terrain généré
  python -m terrain_gen.erosion --demo
            """
        )
        
        # Arguments principaux
        parser.add_argument(
            "input", 
            nargs="?", 
            help="Fichier heightmap d'entrée (PNG ou RAW). Si non fourni, génère un terrain aléatoire"
        )
        parser.add_argument(
            "--output", "-o",
            default="output/eroded_heightmap.png",
            help="Fichier de sortie (défaut: output/eroded_heightmap.png)"
        )
        parser.add_argument(
            "--iterations", "-i",
            type=int,
            default=50,
            help="Nombre d'itérations de simulation (défaut: 50)"
        )
        
        # Paramètres hydrauliques
        parser.add_argument(
            "--rain-rate",
            type=float,
            default=0.01,
            help="Taux de pluie par itération (défaut: 0.01)"
        )
        parser.add_argument(
            "--evap-rate",
            type=float,
            default=0.1,
            help="Taux d'évaporation 0-1 (défaut: 0.1)"
        )
        parser.add_argument(
            "--sed-capacity",
            type=float,
            default=1.0,
            help="Capacité de transport de sédiments (défaut: 1.0)"
        )
        parser.add_argument(
            "--dissolve-rate",
            type=float,
            default=0.1,
            help="Taux de dissolution 0-1 (défaut: 0.1)"
        )
        parser.add_argument(
            "--deposit-rate",
            type=float,
            default=0.1,
            help="Taux de dépôt 0-1 (défaut: 0.1)"
        )
        
        # Paramètres thermiques
        parser.add_argument(
            "--thermal-angle",
            type=float,
            default=30.0,
            help="Angle critique pour érosion thermique en degrés (défaut: 30.0)"
        )
        parser.add_argument(
            "--thermal-rate",
            type=float,
            default=0.1,
            help="Taux d'érosion thermique 0-1 (défaut: 0.1)"
        )
        
        # Paramètres généraux
        parser.add_argument(
            "--gravity",
            type=float,
            default=9.81,
            help="Accélération gravitationnelle (défaut: 9.81)"
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Graine pour reproductibilité (défaut: 42)"
        )
        parser.add_argument(
            "--size",
            type=int,
            default=512,
            help="Taille du terrain généré si aucun fichier d'entrée (défaut: 512)"
        )
        
        # Options spéciales
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Lancer la démonstration avec terrain généré"
        )
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Afficher les détails de simulation"
        )
        parser.add_argument(
            "--save-raw",
            action="store_true",
            help="Sauvegarder aussi en format RAW (Float32)"
        )
        
        args = parser.parse_args()
        
        # Mode démonstration
        if args.demo:
            demo()
            return
        
        # Validation des paramètres
        if args.iterations < 1:
            print("Erreur: Le nombre d'itérations doit être ≥ 1", file=sys.stderr)
            sys.exit(1)
        
        if not (0 <= args.evap_rate <= 1):
            print("Erreur: Le taux d'évaporation doit être entre 0 et 1", file=sys.stderr)
            sys.exit(1)
        
        if not (0 <= args.dissolve_rate <= 1):
            print("Erreur: Le taux de dissolution doit être entre 0 et 1", file=sys.stderr)
            sys.exit(1)
        
        if not (0 <= args.deposit_rate <= 1):
            print("Erreur: Le taux de dépôt doit être entre 0 et 1", file=sys.stderr)
            sys.exit(1)
        
        if not (0 <= args.thermal_rate <= 1):
            print("Erreur: Le taux d'érosion thermique doit être entre 0 et 1", file=sys.stderr)
            sys.exit(1)
        
        # Chargement ou génération du terrain
        if args.input:
            input_path = Path(args.input)
            if not input_path.exists():
                print(f"Erreur: Fichier d'entrée '{args.input}' introuvable", file=sys.stderr)
                sys.exit(1)
            
            print(f"Chargement du terrain: {args.input}")
            
            # Détection du format
            if input_path.suffix.lower() == '.png':
                try:
                    from PIL import Image
                    img = Image.open(input_path)
                    heightmap = np.array(img).astype(np.float32) / 65535.0  # 16-bit PNG
                    if heightmap.ndim == 3:
                        heightmap = heightmap[:, :, 0]  # Prendre le premier canal
                except ImportError:
                    print("Erreur: PIL/Pillow requis pour les fichiers PNG", file=sys.stderr)
                    sys.exit(1)
            elif input_path.suffix.lower() == '.raw':
                heightmap = np.fromfile(input_path, dtype=np.float32)
                # Essayer de deviner la forme
                size = int(np.sqrt(heightmap.size))
                if size * size == heightmap.size:
                    heightmap = heightmap.reshape(size, size)
                else:
                    print("Erreur: Format RAW non reconnu", file=sys.stderr)
                    sys.exit(1)
            else:
                print("Erreur: Format de fichier non supporté. Utilisez PNG ou RAW", file=sys.stderr)
                sys.exit(1)
        else:
            # Génération d'un terrain aléatoire
            print(f"Génération d'un terrain aléatoire {args.size}x{args.size}")
            np.random.seed(args.seed)
            heightmap = np.random.rand(args.size, args.size).astype(np.float32)
        
        print(f"Terrain d'entrée: {heightmap.shape[0]}x{heightmap.shape[1]}")
        print(f"Altitude min/max: {heightmap.min():.3f}/{heightmap.max():.3f}")
        
        # Paramètres d'érosion
        params = {
            "rain_rate": args.rain_rate,
            "evap_rate": args.evap_rate,
            "sed_capacity": args.sed_capacity,
            "dissolve_rate": args.dissolve_rate,
            "deposit_rate": args.deposit_rate,
            "thermal_angle": args.thermal_angle,
            "thermal_rate": args.thermal_rate,
            "gravity": args.gravity,
            "seed": args.seed
        }
        
        if args.verbose:
            print("\nParamètres d'érosion:")
            for key, value in params.items():
                print(f"  {key}: {value}")
            print()
        
        # Application de l'érosion
        print(f"Application de l'érosion ({args.iterations} itérations)...")
        eroded, metrics = erosion(heightmap, n_iters=args.iterations, params=params)
        
        # Affichage des résultats
        print(f"\nRésultats:")
        print(f"  Terrain érodé: {eroded.shape[0]}x{eroded.shape[1]}")
        print(f"  Altitude min/max: {eroded.min():.3f}/{eroded.max():.3f}")
        print(f"  Temps de simulation: {metrics['cpu_time_seconds']:.2f}s")
        print(f"  Conservation de masse: {metrics['mass_conservation_percent']:.6f}")
        
        # Sauvegarde
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarde PNG
        try:
            from PIL import Image
            # Conversion en 16-bit PNG
            eroded_16bit = (eroded * 65535.0).astype(np.uint16)
            img = Image.fromarray(eroded_16bit, mode='I;16')
            img.save(output_path)
            print(f"  Sauvegardé: {output_path}")
        except ImportError:
            print("Erreur: PIL/Pillow requis pour sauvegarder en PNG", file=sys.stderr)
            sys.exit(1)
        
        # Sauvegarde RAW optionnelle
        if args.save_raw:
            raw_path = output_path.with_suffix('.raw')
            eroded.astype(np.float32).tofile(raw_path)
            print(f"  Sauvegardé: {raw_path}")
        
        print("Érosion terminée avec succès ✓")
    
    main()