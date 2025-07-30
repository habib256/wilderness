#!/usr/bin/env python3
"""
Générateur de heightmap 4K de l'île d'Honshu (Japon) avec données réelles.

Ce script génère une heightmap haute résolution 4096x4096 de l'île d'Honshu
en utilisant les données d'élévation SRTM depuis les APIs internet.
"""

import sys
import os
from pathlib import Path
import time

# Ajoute le module terrain_gen au path
project_root = Path(__file__).parent.parent  # Remonte d'un niveau
sys.path.insert(0, str(project_root))

try:
    from terrain_gen.real_terrain_extractor import HonshuTerrainExtractor
    from terrain_gen.progress import ProgressTracker, ConsoleProgressCallback, set_progress_tracker
    import numpy as np
    from PIL import Image
    print("✅ Modules terrain_gen importés avec succès")
except ImportError as e:
    print("❌ Erreur d'import:")
    print(f"   {e}")
    print("💡 Installez les dépendances: pip install -r requirements.txt")
    sys.exit(1)

def main():
    """Génération heightmap 4K d'Honshu."""
    
    print("🏔️ Génération Heightmap Haute Résolution - Île d'Honshu (Japon)")
    print("=" * 68)
    print("🎯 Priorité: Données NATIVES sans upscaling artificiel")
    print("📐 Résolution: Maximum disponible en données réelles")
    print("📡 Source: NASA SRTM (Shuttle Radar Topography Mission)")
    print("🗾 Zone: Île principale du Japon (1,227 km de long)")
    print("⚠️  Attention: Ce processus peut prendre plusieurs minutes")
    print()
    
    # Vérifie la connexion internet
    try:
        import requests
        response = requests.get("https://httpbin.org/ip", timeout=10)
        if response.status_code == 200:
            print("✅ Connexion internet OK")
        else:
            print("⚠️ Connexion internet limitée")
    except Exception:
        print("❌ Pas de connexion internet - l'extraction échouera")
        return
    
    # Estime la taille du téléchargement
    print("📊 Approche:")
    print("   • Données SRTM natives 30m-90m résolution")
    print("   • AUCUN upscaling ou interpolation artificielle")
    print("   • Résolution finale: Dépend des données disponibles")
    print("   • Qualité: 100% données réelles mesurées")
    print("   • Taille estimée: 15-100 MB selon résolution obtenue")
    print("   • Zones disponibles: full, kansai, kanto, alps")
    print()
    
    # Sélection de la zone
    print("🗾 Zones disponibles:")
    print("   1. full    - Île complète d'Honshu (824 × 1,364 km)")
    print("   2. kansai  - Région Kansai/Kinki (Osaka, Kyoto, Nara)")
    print("   3. kanto   - Région Kanto (Tokyo, mont Fuji)")
    print("   4. alps    - Alpes japonaises (montagnes centrales)")
    print()
    
    zone_choice = input("Choisissez une zone [1-4] ou [full/kansai/kanto/alps] (défaut: full): ").lower().strip()
    
    zone_map = {
        "1": "full", "full": "full",
        "2": "kansai", "kansai": "kansai", 
        "3": "kanto", "kanto": "kanto",
        "4": "alps", "alps": "alps"
    }
    
    zone = zone_map.get(zone_choice, "full")
     
    print(f"Zone sélectionnée: {zone}")
    print()
    
    # Demande confirmation
    response = input("Continuer ? [y/N]: ").lower().strip()
    if response not in ['y', 'yes', 'o', 'oui']:
        print("❌ Génération annulée")
        return
    
    # Configure le système de progression
    progress_tracker = ProgressTracker()
    console_callback = ConsoleProgressCallback(show_details=True)
    progress_tracker.add_callback(console_callback)
    set_progress_tracker(progress_tracker)
    progress_tracker.start()
    
    # Crée le dossier de sortie
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    start_time = time.time()
    
    try:
        # Initialise l'extracteur
        print("\n🔧 Initialisation de l'extracteur Honshu...")
        extractor = HonshuTerrainExtractor()
        
        # Affiche les informations de la zone
        zone_info = {
            "full": {
                "name": "Île complète d'Honshu",
                "center": "37.84°N, 135.53°E",
                "dimensions": "824 × 1,364 km",
                "description": "Île principale du Japon, du Kansai au Tohoku"
            },
            "kansai": {
                "name": "Région Kansai",
                "center": "34.80°N, 135.65°E", 
                "dimensions": "222 × 189 km",
                "description": "Osaka, Kyoto, Nara, Kobe"
            },
            "kanto": {
                "name": "Région Kanto",
                "center": "35.75°N, 139.50°E",
                "dimensions": "167 × 167 km", 
                "description": "Tokyo, Yokohama, mont Fuji"
            },
            "alps": {
                "name": "Alpes japonaises",
                "center": "36.15°N, 137.75°E",
                "dimensions": "144 × 167 km",
                "description": "Chaîne montagneuse centrale, sommets >3000m"
            }
        }
        
        info = zone_info[zone]
        print(f"\n📡 Extraction données natives haute résolution...")
        print(f"   📍 Zone: {info['name']}")
        print(f"   🎯 Centre: {info['center']}")
        print(f"   📐 Dimensions: {info['dimensions']}")
        print(f"   ℹ️  Description: {info['description']}")
        print(f"   🚀 Stratégie: Résolution native maximale disponible")
        print()
        
        # Appel extraction native haute résolution
        heightmap = extractor.extract_honshu_4k(zone=zone)
        
        if heightmap is not None:
            elapsed_time = time.time() - start_time
            
            # Détermine le nom de fichier basé sur la résolution réelle
            resolution = heightmap.shape[0]
            if resolution >= 3000:
                base_name = f"honshu_{zone}_4k"
            elif resolution >= 1800:
                base_name = f"honshu_{zone}_2k"  
            elif resolution >= 1200:
                base_name = f"honshu_{zone}_hd"
            else:
                base_name = f"honshu_{zone}_native"
                
            output_png = output_dir / f"{base_name}.png"
            output_web = Path("web/images") / f"{base_name}.png"
            
            print(f"\n💾 Sauvegarde des fichiers...")
            
            # Sauvegarde PNG 16-bit principal
            data_16bit = (heightmap * 65535).astype(np.uint16)
            img = Image.fromarray(data_16bit, mode='I;16')
            img.save(output_png)
            
            # Copie vers web/images pour utilisation immédiate
            if output_web.parent.exists():
                img.save(output_web)
                print(f"   ✅ Copié vers web/images pour utilisation immédiate")
            
            # Sauvegarde PNG 8-bit pour visualisation
            output_8bit = output_dir / f"{base_name}_preview.png"
            data_8bit = (heightmap * 255).astype(np.uint8)
            img_8bit = Image.fromarray(data_8bit, mode='L')
            img_8bit.save(output_8bit)
            
            # Sauvegarde données raw
            output_raw = output_dir / f"{base_name}.raw"
            heightmap.astype(np.float32).tofile(output_raw)
            
            # Calcule la précision par zone
            zone_km = {
                "full": (824, 1364),
                "kansai": (222, 189),
                "kanto": (167, 167),
                "alps": (144, 167)
            }
            
            lat_km, lon_km = zone_km[zone]
            meters_per_pixel = (lat_km * 1000) / resolution
            
            print(f"\n🎉 Extraction native réussie!")
            print(f"⏱️  Temps total: {elapsed_time:.1f} secondes")
            print(f"📊 Statistiques:")
            print(f"   • Résolution: {resolution}x{resolution} pixels")
            print(f"   • Précision: ~{meters_per_pixel:.1f}m par pixel")
            print(f"   • Min: {np.min(heightmap):.4f}")
            print(f"   • Max: {np.max(heightmap):.4f}")
            print(f"   • Moyenne: {np.mean(heightmap):.4f}")
            print(f"   • Écart-type: {np.std(heightmap):.4f}")
            print(f"   • Taille mémoire: {heightmap.nbytes / 1024 / 1024:.1f} MB")
            print(f"   • 🎯 Données 100% natives (aucun upscaling)")
            
            print(f"\n📁 Fichiers générés:")
            print(f"   • {output_png} ({output_png.stat().st_size / 1024 / 1024:.1f} MB)")
            print(f"   • {output_8bit} (preview)")
            print(f"   • {output_raw} (données raw)")
            if output_web.exists():
                print(f"   • {output_web} (web ready)")
            
            print(f"\n🌐 Utilisation:")
            print(f"   • Fichier prêt pour visualisation web")
            print(f"   • Compatible avec l'interface terrain")
            ratio = (resolution / 1024) ** 2
            print(f"   • Résolution {ratio:.1f}x supérieure à la version 1K")
            
            # Info géographique détaillée
            altitude_info = {
                "full": "Mont Fuji (3,776m), Alpes japonaises (>3,000m)",
                "kansai": "Mont Yoshino (858m), collines d'Osaka",
                "kanto": "Mont Fuji (3,776m), monts Tanzawa", 
                "alps": "Mont Hotaka (3,190m), mont Yari (3,180m)"
            }
            
            print(f"\n🗺️ Détails géographiques - {info['name']}:")
            print(f"   • Résolution terrain: ~{meters_per_pixel:.1f}m par pixel")
            print(f"   • Couverture: {info['description']}")
            print(f"   • Points culminants: {altitude_info[zone]}")
            print(f"   • Source: NASA SRTM données natives")
            print(f"   • Précision verticale: ±16m (SRTM)")
            print(f"   • ✅ Qualité: Données mesurées réelles")
            
        else:
            print(f"\n❌ Échec de l'extraction haute résolution")
            print(f"💡 Causes possibles:")
            print(f"   • Connexion internet insuffisante")
            print(f"   • Services SRTM temporairement indisponibles")
            print(f"   • Quotas API dépassés")
            print(f"   • Toutes les résolutions natives ont échoué")
            print(f"   • Zone trop large pour les APIs disponibles")
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Génération interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur lors de la génération haute résolution:")
        print(f"   {e}")
        print(f"💡 Solutions:")
        print(f"   • Vérifiez votre connexion internet")
        print(f"   • Assurez-vous d'avoir assez de RAM (>2GB libre)")
        print(f"   • Réessayez avec une zone plus petite")
        print(f"   • Vérifiez que rasterio est installé: pip install rasterio")

if __name__ == "__main__":
    main()