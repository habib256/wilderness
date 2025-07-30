#!/usr/bin/env python3
"""
Exemple d'utilisation de l'extracteur de terrain réel pour l'île de la Réunion.

Ce script démontre comment utiliser ReunionTerrainExtractor pour récupérer
les données d'élévation réelles de la Réunion depuis internet et les intégrer
avec le système de génération existant.
"""

import numpy as np
from pathlib import Path
import logging
from .real_terrain_extractor import ReunionTerrainExtractor, ReunionTerrainBounds
from .heightmap import HeightMapGenerator
from .progress import ProgressTracker, ConsoleProgressCallback, set_progress_tracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_reunion_extraction():
    """Démontre l'extraction complète de la Réunion."""
    
    print("🏝️ Démonstration - Extraction terrain réel de la Réunion")
    print("=" * 60)
    
    # Configure le système de progression
    progress_tracker = ProgressTracker()
    console_callback = ConsoleProgressCallback(show_details=True)
    progress_tracker.add_callback(console_callback)
    set_progress_tracker(progress_tracker)
    progress_tracker.start()
    
    # Crée le dossier de sortie
    output_dir = Path("output/reunion_real")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialise l'extracteur
    extractor = ReunionTerrainExtractor()
    
    # Extrait les différentes zones
    zones = [
        ("full", "Île complète"),
        ("central", "Massifs centraux (Piton des Neiges, Piton de la Fournaise)"),
        ("west", "Côte ouest (Saint-Denis, Saint-Paul)")
    ]
    
    results = {}
    
    for zone_key, zone_desc in zones:
        print(f"\n📍 Zone: {zone_desc}")
        print("-" * 40)
        
        heightmap = extractor.extract_reunion_1k(zone=zone_key)
        
        if heightmap is not None:
            # Sauvegarde la heightmap
            output_file = output_dir / f"reunion_{zone_key}_1k.png"
            
            data_16bit = (heightmap * 65535).astype(np.uint16)
            from PIL import Image
            img = Image.fromarray(data_16bit, mode='I;16')
            img.save(output_file)
            
            # Statistiques
            stats = {
                'min': np.min(heightmap),
                'max': np.max(heightmap),
                'mean': np.mean(heightmap),
                'std': np.std(heightmap),
                'file': str(output_file)
            }
            
            results[zone_key] = stats
            
            print(f"✅ Zone {zone_key} extraite avec succès:")
            print(f"   • Résolution: 1024x1024")
            print(f"   • Min: {stats['min']:.4f}")
            print(f"   • Max: {stats['max']:.4f}")
            print(f"   • Moyenne: {stats['mean']:.4f}")
            print(f"   • Écart-type: {stats['std']:.4f}")
            print(f"   • Fichier: {stats['file']}")
            
        else:
            print(f"❌ Échec de l'extraction pour la zone {zone_key}")
            results[zone_key] = None
    
    # Résumé final
    print(f"\n📊 Résumé de l'extraction")
    print("=" * 40)
    
    successful_zones = [k for k, v in results.items() if v is not None]
    failed_zones = [k for k, v in results.items() if v is None]
    
    print(f"✅ Zones réussies: {len(successful_zones)}/{len(zones)}")
    if successful_zones:
        print(f"   {', '.join(successful_zones)}")
    
    if failed_zones:
        print(f"❌ Zones échouées: {len(failed_zones)}")
        print(f"   {', '.join(failed_zones)}")
    
    # Comparaison avec terrain généré
    if "full" in results and results["full"]:
        print(f"\n🔄 Comparaison avec terrain procédural")
        demo_comparison_with_generated(results["full"], output_dir)
    
    print(f"\n🎯 Tous les fichiers sauvegardés dans: {output_dir}")
    

def demo_comparison_with_generated(real_stats, output_dir):
    """Compare le terrain réel avec un terrain généré procéduralement."""
    print("-" * 40)
    
    # Génère un terrain procédural de référence
    generator = HeightMapGenerator(size=1024, seed=42)
    generator.configure(
        ds_roughness=0.7,  # Rugosité élevée pour simuler le volcanique
        fbm_octaves=8,     # Détails élevés
        fbm_frequency=0.008,
        blend_ratio=0.6
    )
    
    generated_heightmap = generator.generate()
    
    # Sauvegarde le terrain généré
    generated_file = output_dir / "reunion_generated_comparison_1k.png"
    generator.save_png(generated_heightmap, str(generated_file))
    
    # Statistiques comparatives
    gen_stats = {
        'min': np.min(generated_heightmap),
        'max': np.max(generated_heightmap),
        'mean': np.mean(generated_heightmap),
        'std': np.std(generated_heightmap)
    }
    
    print(f"Comparaison Terrain Réel vs Procédural:")
    print(f"                      │  Réel     │  Généré  │  Diff")
    print(f"──────────────────────┼───────────┼──────────┼────────")
    print(f"Min                   │ {real_stats['min']:8.4f} │ {gen_stats['min']:8.4f} │ {abs(real_stats['min'] - gen_stats['min']):6.4f}")
    print(f"Max                   │ {real_stats['max']:8.4f} │ {gen_stats['max']:8.4f} │ {abs(real_stats['max'] - gen_stats['max']):6.4f}")
    print(f"Moyenne               │ {real_stats['mean']:8.4f} │ {gen_stats['mean']:8.4f} │ {abs(real_stats['mean'] - gen_stats['mean']):6.4f}")
    print(f"Écart-type            │ {real_stats['std']:8.4f} │ {gen_stats['std']:8.4f} │ {abs(real_stats['std'] - gen_stats['std']):6.4f}")
    
    # Calcul de similarité approximative
    similarity = 1.0 - (
        abs(real_stats['mean'] - gen_stats['mean']) + 
        abs(real_stats['std'] - gen_stats['std'])
    ) / 2.0
    
    print(f"\n📈 Similarité estimée: {similarity * 100:.1f}%")
    print(f"💾 Terrain généré sauvé: {generated_file}")


def demo_coordinates_info():
    """Affiche les informations sur les coordonnées de la Réunion."""
    print("\n🗺️ Informations géographiques - Île de la Réunion")
    print("=" * 50)
    
    zones = [
        ("Île complète", ReunionTerrainBounds.FULL_ISLAND),
        ("Massifs centraux", ReunionTerrainBounds.CENTRAL_MOUNTAINS),
        ("Côte ouest", ReunionTerrainBounds.WEST_COAST)
    ]
    
    for name, bounds in zones:
        center_lat, center_lon = bounds.center()
        lat_km, lon_km = bounds.dimensions_km()
        
        print(f"\n📍 {name}:")
        print(f"   • Limites: {bounds.north:.3f}°N à {bounds.south:.3f}°S")
        print(f"             {bounds.west:.3f}°W à {bounds.east:.3f}°E")
        print(f"   • Centre: {abs(center_lat):.3f}°S, {center_lon:.3f}°E")
        print(f"   • Dimensions: {lat_km:.1f} × {lon_km:.1f} km")
        print(f"   • Surface: ~{lat_km * lon_km:.0f} km²")


def main():
    """Point d'entrée principal de la démonstration."""
    try:
        # Affiche les informations géographiques
        demo_coordinates_info()
        
        # Lance l'extraction complète
        demo_reunion_extraction()
        
        print(f"\n🎉 Démonstration terminée avec succès!")
        print(f"🌐 Les heightmaps peuvent maintenant être utilisées dans l'interface web 3D.")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Démonstration interrompue par l'utilisateur.")
    except Exception as e:
        logger.error(f"Erreur lors de la démonstration: {e}")
        print(f"\n❌ Erreur: {e}")
        print(f"💡 Vérifiez votre connexion internet et les dépendances (rasterio).")


if __name__ == "__main__":
    main()