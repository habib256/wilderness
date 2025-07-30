#!/usr/bin/env python3
"""
Exemple d'utilisation du module terrain_gen.

Génère différents types de terrain pour démontrer les capacités
avec suivi de progression en temps réel.
"""

import os
from pathlib import Path
from terrain_gen import (
    HeightMapGenerator, ProgressTracker, ConsoleProgressCallback,
    set_progress_tracker
)

def main():
    """Génère plusieurs exemples de terrain."""
    
    # Crée le dossier de sortie
    output_dir = Path("output/examples")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🏔️  Génération d'exemples de terrain...")
    
    # Exemple 1: Terrain montagneux
    print("\n1. Terrain montagneux...")
    generator = HeightMapGenerator(size=256, seed=42)
    generator.configure(
        ds_roughness=0.8,     # Très rugueux
        fbm_octaves=8,        # Beaucoup de détail
        blend_ratio=0.8       # Dominance Diamond-Square
    )
    
    heightmap = generator.generate()
    generator.save_png(heightmap, output_dir / "montagneux.png")
    print(f"   ✓ Sauvegardé: {output_dir}/montagneux.png")
    
    # Exemple 2: Terrain vallonné
    print("\n2. Terrain vallonné...")
    generator = HeightMapGenerator(size=256, seed=123)
    generator.configure(
        ds_roughness=0.4,     # Doux
        fbm_octaves=4,        # Moins de détail
        blend_ratio=0.3       # Dominance fBm
    )
    
    heightmap = generator.generate()
    generator.save_png(heightmap, output_dir / "vallonne.png")
    print(f"   ✓ Sauvegardé: {output_dir}/vallonne.png")
    
    # Exemple 3: Plaines avec détails
    print("\n3. Plaines détaillées...")
    generator = HeightMapGenerator(size=256, seed=456)
    generator.configure(
        ds_roughness=0.2,     # Très lisse
        fbm_frequency=0.02,   # Features plus fines
        blend_ratio=0.1       # Presque que fBm
    )
    
    heightmap = generator.generate()
    generator.save_png(heightmap, output_dir / "plaines.png")
    print(f"   ✓ Sauvegardé: {output_dir}/plaines.png")
    
    # Exemple 4: Archipel
    print("\n4. Archipel...")
    generator = HeightMapGenerator(size=256, seed=789)
    generator.configure(
        ds_roughness=0.6,
        fbm_octaves=6,
        fbm_frequency=0.008,  # Features moyennes
        blend_ratio=0.5       # Équilibré
    )
    
    heightmap = generator.generate()
    
    # Applique un seuil pour créer des îles
    import numpy as np
    threshold = 0.4
    heightmap = np.where(heightmap > threshold, 
                        (heightmap - threshold) / (1 - threshold), 
                        0)
    
    generator.save_png(heightmap, output_dir / "archipel.png")
    print(f"   ✓ Sauvegardé: {output_dir}/archipel.png")
    
    print(f"\n🎉 Tous les exemples générés dans {output_dir}/")
    print("\nUtilisez un visualiseur d'images pour voir les résultats !")

if __name__ == "__main__":
    main() 