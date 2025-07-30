#!/usr/bin/env python3
"""
Script pour générer les terrains érodés pour le visualiseur web.

Génère les heightmaps érodées avec différentes intensités
et les copie dans le dossier web/images/.
"""

import os
import shutil
import logging
from pathlib import Path

from terrain_gen.heightmap import HeightMapGenerator
from terrain_gen.erosion import erode_heightmap
from terrain_gen.progress import ConsoleProgressCallback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_eroded_terrains():
    """Génère les terrains érodés pour le visualiseur."""
    
    # Configuration
    size = 1024
    seed = 42
    
    # Dossiers
    output_dir = Path("output")
    web_images_dir = Path("web/images")
    
    # Création des dossiers
    output_dir.mkdir(exist_ok=True)
    web_images_dir.mkdir(exist_ok=True)
    
    logger.info(f"Génération des terrains érodés {size}x{size} (seed: {seed})")
    
    # Génération du terrain de base
    logger.info("1. Génération du terrain de base...")
    generator = HeightMapGenerator(size=size, seed=seed)
    base_heightmap = generator.generate()
    
    # Sauvegarde du terrain de base
    base_filename = output_dir / "base_heightmap.png"
    generator.save_png(base_heightmap, str(base_filename))
    logger.info(f"   Terrain de base sauvegardé: {base_filename}")
    
    # Érosion légère
    logger.info("2. Application de l'érosion légère...")
    eroded_light = erode_heightmap(base_heightmap, "light", ConsoleProgressCallback())
    light_filename = output_dir / "eroded_light.png"
    generator.save_png(eroded_light, str(light_filename))
    logger.info(f"   Érosion légère terminée: {light_filename}")
    
    # Érosion moyenne
    logger.info("3. Application de l'érosion moyenne...")
    eroded_medium = erode_heightmap(base_heightmap, "medium", ConsoleProgressCallback())
    medium_filename = output_dir / "eroded_medium.png"
    generator.save_png(eroded_medium, str(medium_filename))
    logger.info(f"   Érosion moyenne terminée: {medium_filename}")
    
    # Érosion forte
    logger.info("4. Application de l'érosion forte...")
    eroded_heavy = erode_heightmap(base_heightmap, "heavy", ConsoleProgressCallback())
    heavy_filename = output_dir / "eroded_heavy.png"
    generator.save_png(eroded_heavy, str(heavy_filename))
    logger.info(f"   Érosion forte terminée: {heavy_filename}")
    
    # Copie vers web/images/
    logger.info("5. Copie vers web/images/...")
    
    files_to_copy = [
        (light_filename, web_images_dir / "eroded_light.png"),
        (medium_filename, web_images_dir / "eroded_medium.png"),
        (heavy_filename, web_images_dir / "eroded_heavy.png")
    ]
    
    for src, dst in files_to_copy:
        if src.exists():
            shutil.copy2(src, dst)
            logger.info(f"   Copié: {dst}")
        else:
            logger.error(f"   Fichier source manquant: {src}")
    
    # Statistiques
    logger.info("\n📊 Statistiques des terrains érodés:")
    
    terrains = [
        ("Base", base_heightmap),
        ("Léger", eroded_light),
        ("Moyen", eroded_medium),
        ("Fort", eroded_heavy)
    ]
    
    for name, terrain in terrains:
        print(f"   {name:6}: min={terrain.min():.4f}, max={terrain.max():.4f}, "
              f"moy={terrain.mean():.4f}, std={terrain.std():.4f}")
    
    # Différences
    print(f"\n📈 Différences par rapport au terrain de base:")
    for name, terrain in terrains[1:]:
        diff_mean = abs(terrain - base_heightmap).mean()
        print(f"   {name:6}: différence moyenne = {diff_mean:.4f}")
    
    logger.info("\n✅ Génération des terrains érodés terminée!")
    logger.info("Les terrains sont maintenant disponibles dans le visualiseur web.")


def main():
    """Point d'entrée principal."""
    try:
        generate_eroded_terrains()
    except KeyboardInterrupt:
        logger.info("\n❌ Génération interrompue par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération: {e}")
        raise


if __name__ == "__main__":
    main() 