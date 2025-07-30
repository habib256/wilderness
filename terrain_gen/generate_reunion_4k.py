#!/usr/bin/env python3
"""
Générateur de heightmap 4K de l'île de la Réunion avec données réelles.

Ce script génère une heightmap haute résolution 4096x4096 de l'île de la Réunion
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
    from terrain_gen.real_terrain_extractor import ReunionTerrainExtractor
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
    """Génération heightmap 4K de la Réunion."""
    
    print("🏝️ Génération Heightmap Haute Résolution - Île de la Réunion")
    print("=" * 62)
    print("🎯 Priorité: Données NATIVES sans upscaling artificiel")
    print("📐 Résolution: Maximum disponible en données réelles")
    print("📡 Source: NASA SRTM (Shuttle Radar Topography Mission)")
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
    print("   • Taille estimée: 5-30 MB selon résolution obtenue")
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
        print("\n🔧 Initialisation de l'extracteur...")
        extractor = ReunionTerrainExtractor()
        
        # Extraction données natives haute résolution
        print("\n📡 Extraction données natives haute résolution...")
        print("   📍 Zone: Île complète")
        print("   📏 Coordonnées: 21.13°S, 55.53°E")
        print("   📐 Dimensions: ~58 × 69 km")
        print("   🎯 Stratégie: Résolution native maximale disponible")
        print()
        
        # Appel extraction native haute résolution
        heightmap = extractor.extract_reunion_4k()
        
        if heightmap is not None:
            elapsed_time = time.time() - start_time
            
            # Détermine le nom de fichier basé sur la résolution réelle
            resolution = heightmap.shape[0]
            if resolution >= 3000:
                base_name = "reunion_real_4k"
            elif resolution >= 1800:
                base_name = "reunion_real_2k"  
            elif resolution >= 1200:
                base_name = "reunion_real_hd"
            else:
                base_name = "reunion_real_native"
                
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
            
            # Statistiques finales avec résolution réelle
            resolution = heightmap.shape[0]
            lat_km, lon_km = 58, 69  # Dimensions approximatives de la Réunion
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
            print(f"   • Remplacez reunion_real_1k.png par {base_name}.png")
            print(f"   • Mise à jour automatique dans l'interface web")
            ratio = (resolution / 1024) ** 2
            print(f"   • Résolution {ratio:.1f}x supérieure à la version 1K")
            
            # Info géographique détaillée
            print(f"\n🗺️ Détails géographiques:")
            print(f"   • Résolution terrain: ~{meters_per_pixel:.1f}m par pixel")
            print(f"   • Couverture: Île complète de la Réunion")
            print(f"   • Point culminant: Piton des Neiges (3,070m)")
            print(f"   • Volcan actif: Piton de la Fournaise")
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
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Génération interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur lors de la génération haute résolution:")
        print(f"   {e}")
        print(f"💡 Solutions:")
        print(f"   • Vérifiez votre connexion internet")
        print(f"   • Assurez-vous d'avoir assez de RAM (>1GB libre)")
        print(f"   • Réessayez avec la version 1K standard")
        print(f"   • Vérifiez que rasterio est installé: pip install rasterio")

if __name__ == "__main__":
    main()