#!/usr/bin/env python3
"""
Script de démonstration pour l'extraction du terrain réel de l'île de la Réunion.

Usage:
    python demo_reunion.py
    
Ce script va télécharger les données d'élévation réelles de la Réunion
et créer une heightmap 1024x1024 utilisable dans votre projet.
"""

import sys
import os
from pathlib import Path

# Ajoute le module terrain_gen au path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from terrain_gen.real_terrain_extractor import ReunionTerrainExtractor
    from terrain_gen.progress import ProgressTracker, ConsoleProgressCallback, set_progress_tracker
    print("✅ Modules terrain_gen importés avec succès")
except ImportError as e:
    print("❌ Erreur d'import:")
    print(f"   {e}")
    print("💡 Installez les dépendances: pip install -r requirements.txt")
    sys.exit(1)

def main():
    """Démonstration simple de l'extraction Réunion."""
    
    print("🏝️ Démonstration - Extraction terrain réel de la Réunion")
    print("=" * 60)
    print("Ce script va récupérer les données d'élévation réelles de l'île")
    print("de la Réunion depuis internet et créer une heightmap 1024x1024.")
    print()
    
    # Vérifie la connexion internet (simple test)
    try:
        import requests
        response = requests.get("https://httpbin.org/ip", timeout=10)
        if response.status_code == 200:
            print("✅ Connexion internet OK")
        else:
            print("⚠️ Connexion internet limitée")
    except Exception:
        print("❌ Pas de connexion internet - l'extraction échouera")
        print("💡 Vérifiez votre connexion et réessayez")
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
    
    try:
        # Initialise l'extracteur
        print("\n🔧 Initialisation de l'extracteur...")
        extractor = ReunionTerrainExtractor()
        
        # Extrait l'île complète (zone par défaut)
        print("\n📡 Extraction des données de la Réunion...")
        print("   Source: NASA SRTM (Shuttle Radar Topography Mission)")
        print("   Résolution: 30m par pixel")
        print("   Taille finale: 1024x1024")
        print()
        
        heightmap = extractor.extract_reunion_1k(zone="full")
        
        if heightmap is not None:
            # Sauvegarde
            output_file = output_dir / "reunion_real_1k.png"
            
            # Convertit en PNG 16-bit
            import numpy as np
            from PIL import Image
            
            data_16bit = (heightmap * 65535).astype(np.uint16)
            img = Image.fromarray(data_16bit, mode='I;16')
            img.save(output_file)
            
            # Statistiques
            print(f"\n🎉 Extraction réussie!")
            print(f"📊 Statistiques:")
            print(f"   • Résolution: 1024x1024 pixels")
            print(f"   • Min: {np.min(heightmap):.4f}")
            print(f"   • Max: {np.max(heightmap):.4f}")
            print(f"   • Moyenne: {np.mean(heightmap):.4f}")
            print(f"   • Écart-type: {np.std(heightmap):.4f}")
            print(f"   • Fichier: {output_file}")
            
            print(f"\n🌐 Utilisation:")
            print(f"   • Copiez {output_file} vers web/images/reunion.png")
            print(f"   • Ajoutez 'reunion' aux terrains dans web/index.html")
            print(f"   • Ouvrez web/index.html dans votre navigateur")
            
            # Info sur l'île
            print(f"\n🏝️ À propos de l'île de la Réunion:")
            print(f"   • Localisation: 21.1°S, 55.5°E (Océan Indien)")
            print(f"   • Dimensions: ~63 × 45 km")
            print(f"   • Point culminant: Piton des Neiges (3,070m)")
            print(f"   • Géologie: Île volcanique active")
            
        else:
            print(f"\n❌ Échec de l'extraction")
            print(f"💡 Causes possibles:")
            print(f"   • Connexion internet instable")
            print(f"   • Services d'élévation temporairement indisponibles")
            print(f"   • Limite de quotas API atteinte")
            print(f"   • Dépendance 'rasterio' manquante")
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Extraction interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur lors de l'extraction:")
        print(f"   {e}")
        print(f"💡 Solutions:")
        print(f"   • Vérifiez votre connexion internet")
        print(f"   • Installez rasterio: pip install rasterio")
        print(f"   • Réessayez dans quelques minutes")

if __name__ == "__main__":
    main()