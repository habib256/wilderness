#!/usr/bin/env python3
"""
Script de génération de heightmap haute résolution pour l'île de Yakushima (Japon).

Yakushima est une île japonaise classée au patrimoine mondial de l'UNESCO,
connue pour ses reliefs granitiques spectaculaires et sa forêt de cèdres millénaires.

Caractéristiques topographiques :
- Mont Miyanoura : 1 936 m (point culminant)
- Gradient altitudinal : Mer → 1 936 m en 13 km
- Relief granitique fracturé avec arêtes radio-convergentes
- 46 sommets > 1 000 m
- Cascade de Senpiro (60 m)
- Forêt de Jōmon-sugi (cèdres > 2 000 ans)

Zones disponibles :
- full : Île complète (site UNESCO)
- central : Zone centrale avec Mont Miyanoura
- jomon : Forêt de Jōmon-sugi
- senpiro : Cascade de Senpiro et ravins
- steep : Zone côte-à-colline la plus abrupte
- wide : Vue large et éloignée (zone étendue)
"""

import sys
import os
from pathlib import Path
import numpy as np
from PIL import Image
import argparse
import logging
from typing import Optional

# Ajoute le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from terrain_gen.real_terrain_extractor import YakushimaTerrainExtractor
from terrain_gen.progress import ProgressTracker, ConsoleProgressCallback, set_progress_tracker

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_yakushima_heightmap(zone: str = "full", 
                                resolution: str = "4k",
                                output_dir: str = "output",
                                api_key: Optional[str] = None) -> bool:
    """
    Génère une heightmap de Yakushima.
    
    Args:
        zone: Zone à extraire ("full", "central", "jomon", "senpiro", "steep")
        resolution: Résolution ("4k" ou "1k")
        output_dir: Répertoire de sortie
        api_key: Clé API OpenTopography (optionnelle)
        
    Returns:
        True si succès, False sinon
    """
    print(f"🌿 Génération heightmap Yakushima - Zone: {zone}, Résolution: {resolution}")
    print("=" * 60)
    
    # Configure le système de progression
    progress_tracker = ProgressTracker()
    console_callback = ConsoleProgressCallback(show_details=True)
    progress_tracker.add_callback(console_callback)
    set_progress_tracker(progress_tracker)
    progress_tracker.start()
    
    try:
        # Crée le répertoire de sortie
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialise l'extracteur
        extractor = YakushimaTerrainExtractor(api_key=api_key)
        
        # Extrait les données selon la résolution
        if resolution == "4k":
            heightmap = extractor.extract_yakushima_4k(zone=zone)
            suffix = "4k"
        else:
            heightmap = extractor.extract_yakushima_1k(zone=zone)
            suffix = "1k"
        
        # Redimensionne à une résolution plus élevée pour la visualisation
        if heightmap is not None and heightmap.shape[0] < 1024:
            from scipy.ndimage import zoom
            scale_factor = 1024 / heightmap.shape[0]
            heightmap = zoom(heightmap, scale_factor, order=1)
            print(f"📏 Redimensionné de {heightmap.shape[0]//scale_factor}×{heightmap.shape[1]//scale_factor} à {heightmap.shape[0]}×{heightmap.shape[1]}")
        
        if heightmap is None:
            logger.error("❌ Échec de l'extraction des données")
            return False
        
        # Informations sur les données extraites
        print(f"\n📊 Données extraites:")
        print(f"   Taille: {heightmap.shape[0]}×{heightmap.shape[1]} pixels")
        print(f"   Altitude min: {heightmap.min():.3f}")
        print(f"   Altitude max: {heightmap.max():.3f}")
        print(f"   Range: [{heightmap.min():.3f}, {heightmap.max():.3f}]")
        
        # Sauvegarde en PNG 16-bit
        progress_tracker.start_stage("SAVING", f"Sauvegarde heightmap Yakushima")
        
        png_filename = f"yakushima_{zone}_{suffix}.png"
        png_path = output_path / png_filename
        
        data_16bit = (heightmap * 65535).astype(np.uint16)
        img = Image.fromarray(data_16bit, mode='I;16')
        img.save(png_path)
        
        print(f"✅ Heightmap sauvegardée: {png_path}")
        
        # Sauvegarde en format RAW (Float32)
        raw_filename = f"yakushima_{zone}_{suffix}.raw"
        raw_path = output_path / raw_filename
        
        heightmap.astype(np.float32).tofile(raw_path)
        print(f"✅ Données RAW sauvegardées: {raw_path}")
        
        # Génère une preview colorée
        preview_filename = f"yakushima_{zone}_{suffix}_preview.png"
        preview_path = output_path / preview_filename
        
        # Crée une preview avec colormap terrain
        preview_data = (heightmap * 255).astype(np.uint8)
        preview_img = Image.fromarray(preview_data, mode='L')
        preview_img.save(preview_path)
        
        print(f"✅ Preview générée: {preview_path}")
        
        # Statistiques finales
        print(f"\n🎯 Statistiques finales:")
        print(f"   Fichier principal: {png_filename}")
        print(f"   Données brutes: {raw_filename}")
        print(f"   Preview: {preview_filename}")
        print(f"   Taille fichier: {png_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération: {e}")
        return False


def main():
    """Interface CLI pour la génération de heightmaps Yakushima."""
    parser = argparse.ArgumentParser(
        description="Générateur de heightmaps haute résolution pour l'île de Yakushima (Japon)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  # Île complète en haute résolution
  python generate_yakushima_4k.py --zone full --resolution 4k
  
  # Zone centrale avec Mont Miyanoura
  python generate_yakushima_4k.py --zone central --resolution 4k
  
  # Forêt de Jōmon-sugi en basse résolution
  python generate_yakushima_4k.py --zone jomon --resolution 1k
  
  # Cascade de Senpiro
  python generate_yakushima_4k.py --zone senpiro --resolution 4k
  
  # Zone côte-à-colline la plus abrupte
  python generate_yakushima_4k.py --zone steep --resolution 4k
  
  # Vue large et éloignée
  python generate_yakushima_4k.py --zone wide --resolution 4k
        """
    )
    
    parser.add_argument(
        "--zone", 
        choices=["full", "central", "jomon", "senpiro", "steep", "wide"],
        default="full",
        help="Zone de Yakushima à extraire (défaut: full)"
    )
    
    parser.add_argument(
        "--resolution",
        choices=["4k", "1k"],
        default="4k",
        help="Résolution de sortie (défaut: 4k)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Répertoire de sortie (défaut: output)"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Clé API OpenTopography (optionnelle)"
    )
    
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Désactive l'affichage de la progression"
    )
    
    args = parser.parse_args()
    
    # Affiche les informations sur Yakushima
    print("🏔️ Île de Yakushima (Japon) - Site UNESCO")
    print("=" * 60)
    print("📍 Coordonnées: 30.358°N, 130.532°E")
    print("🏔️ Mont Miyanoura: 1 936 m (point culminant)")
    print("🌿 Forêt de Jōmon-sugi: Cèdres millénaires")
    print("💧 Cascade de Senpiro: 60 m de hauteur")
    print("🌊 Gradient: Mer → 1 936 m en 13 km")
    print("🏛️ Patrimoine UNESCO depuis 1993")
    print()
    
    # Génère la heightmap
    success = generate_yakushima_heightmap(
        zone=args.zone,
        resolution=args.resolution,
        output_dir=args.output_dir,
        api_key=args.api_key
    )
    
    if success:
        print(f"\n🎉 Génération Yakushima {args.zone} {args.resolution} terminée avec succès!")
        print("🌿 Les fichiers sont disponibles dans le répertoire de sortie.")
    else:
        print(f"\n❌ Échec de la génération Yakushima {args.zone} {args.resolution}")
        sys.exit(1)


if __name__ == "__main__":
    main() 