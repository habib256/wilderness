#!/usr/bin/env python3
"""
Interface CLI pour l'érosion hydraulique.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from .erosion import HydraulicErosion, ErosionPipeline, erode_heightmap
from .heightmap import HeightMapGenerator
from .progress import get_progress_tracker, ProgressStage


def setup_logging(verbose: bool = False) -> None:
    """Configure le système de logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_heightmap(filepath: str) -> np.ndarray:
    """Charge une heightmap PNG (gère 8-bit et 16-bit)."""
    try:
        with Image.open(filepath) as img:
                        # Gestion des images 16-bit ou 32-bit (modes "I;16" ou "I")
            if img.mode in ("I;16", "I"):
                data = np.array(img)
                # Détecte la profondeur : 0-65535 ⇒ 16-bit, sinon on normalise par max
                max_val = data.max() if data.max() > 0 else 65535
                heightmap = data.astype(np.float32) / float(max_val)
            else:
                # Fallback 8-bit : conversion en niveaux de gris puis normalisation 0-1
                if img.mode != "L":
                    img = img.convert("L")
                data = np.array(img, dtype=np.uint8)
                heightmap = data.astype(np.float32) / 255.0
            logging.info(f"Heightmap chargée: {heightmap.shape}, mode={img.mode}")
            return heightmap
    except Exception as e:
        logging.error(f"Erreur lors du chargement de {filepath}: {e}")
        sys.exit(1)


def save_heightmap(heightmap: np.ndarray, filepath: str) -> None:
    """Sauvegarde une heightmap en PNG."""
    try:
        heightmap_normalized = np.clip(heightmap * 255, 0, 255).astype(np.uint8)
        img = Image.fromarray(heightmap_normalized, mode='L')
        img.save(filepath)
        logging.info(f"Heightmap sauvegardée: {filepath}")
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde de {filepath}: {e}")
        sys.exit(1)


def print_heightmap_stats(heightmap: np.ndarray, name: str = "Heightmap") -> None:
    """Affiche les statistiques d'une heightmap."""
    print(f"\n📊 Statistiques {name}:")
    print(f"   Taille: {heightmap.shape[0]}x{heightmap.shape[1]}")
    print(f"   Min: {heightmap.min():.4f}")
    print(f"   Max: {heightmap.max():.4f}")
    print(f"   Moyenne: {heightmap.mean():.4f}")
    print(f"   Écart-type: {heightmap.std():.4f}")
    grad_x = np.gradient(heightmap, axis=1)
    grad_y = np.gradient(heightmap, axis=0)
    roughness = np.sqrt(grad_x**2 + grad_y**2).mean()
    print(f"   Rugosité: {roughness:.4f}")


def main():
    """Fonction principale de l'interface CLI."""
    parser = argparse.ArgumentParser(description="Interface CLI pour l'érosion hydraulique")
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--input', '-i', type=str, help='Fichier heightmap d\'entrée (PNG)')
    input_group.add_argument('--generate', '-g', type=int, metavar='SIZE', help='Générer une heightmap de taille SIZE')
    
    parser.add_argument('--output', '-o', type=str, default='output/eroded_heightmap.png', help='Fichier de sortie')
    parser.add_argument('--intensity', choices=['light', 'medium', 'heavy'], default='medium', help='Intensité d\'érosion')
    parser.add_argument('--iterations', type=int, help='Nombre d\'itérations d\'érosion')
    parser.add_argument('--seed', type=int, default=42, help='Seed pour la génération')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mode verbeux')
    parser.add_argument('--stats', action='store_true', help='Afficher les statistiques avant/après érosion')

    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if args.generate:
        logger.info(f"Génération d'une heightmap {args.generate}x{args.generate}")
        generator = HeightMapGenerator(size=args.generate, seed=args.seed)
        heightmap = generator.generate()
    else:
        logger.info(f"Chargement de la heightmap: {args.input}")
        heightmap = load_heightmap(args.input)

    if args.stats:
        print_heightmap_stats(heightmap, "Initiale")
    
    if args.iterations:
        eroder = HydraulicErosion(iterations=args.iterations, seed=args.seed)
        eroded_heightmap = eroder.erode(heightmap)
    else:
        eroded_heightmap = erode_heightmap(heightmap, args.intensity)

    if args.stats:
        print_heightmap_stats(eroded_heightmap, "Érodée")
    
    save_heightmap(eroded_heightmap, args.output)
    logger.info("Érosion terminée avec succès!")


if __name__ == "__main__":
    main()
