#!/usr/bin/env python3
"""
API Flask pour la regénération des terrains.
Appelé depuis l'interface web pour regénérer les heightmaps.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import sys
import os
from pathlib import Path
import random
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Permet les appels depuis le navigateur

# Configuration des chemins
PROJECT_ROOT = Path(__file__).parent.parent
TERRAIN_GEN_PATH = PROJECT_ROOT / "terrain_gen"
OUTPUT_PATH = PROJECT_ROOT / "web" / "images"

@app.route('/api/regenerate-terrains', methods=['POST'])
def regenerate_terrains():
    """Regénère tous les terrains avec de nouvelles seeds aléatoires."""
    try:
        data = request.get_json()
        terrains_to_generate = data.get('terrains', [])
        
        logger.info(f"🔄 Regénération demandée pour: {terrains_to_generate}")
        
        # Configuration des terrains avec paramètres spécifiques - RÉSOLUTION 16K
        terrain_configs = {
            'montagneux': {
                'size': 4096,  # 16x augmentation
                'ds_roughness': 0.8,
                'fbm_octaves': 8,
                'blend_ratio': 0.8,
                'output': OUTPUT_PATH / "montagneux.png"
            },
            'vallonne': {
                'size': 4096,  # 16x augmentation
                'ds_roughness': 0.4,
                'fbm_octaves': 4,
                'blend_ratio': 0.3,
                'output': OUTPUT_PATH / "vallonne.png"
            },
            'plaines': {
                'size': 4096,  # 16x augmentation
                'ds_roughness': 0.2,
                'fbm_frequency': 0.02,
                'blend_ratio': 0.1,
                'output': OUTPUT_PATH / "plaines.png"
            },
            'archipel': {
                'size': 4096,  # 16x augmentation
                'ds_roughness': 0.6,
                'fbm_octaves': 6,
                'fbm_frequency': 0.008,
                'blend_ratio': 0.5,
                'post_process': 'archipel',  # Applique un seuillage
                'output': OUTPUT_PATH / "archipel.png"
            },
            'heightmap': {
                'size': 2048,  # 16x augmentation (de 128)
                'ds_roughness': 0.6,
                'fbm_octaves': 6,
                'blend_ratio': 0.7,
                'output': OUTPUT_PATH / "heightmap.png"
            },
            'test_heightmap': {
                'size': 64,  # Reste petit pour les tests rapides
                'ds_roughness': 0.5,
                'fbm_octaves': 4,
                'blend_ratio': 0.5,
                'output': OUTPUT_PATH / "test_heightmap.png"
            }
        }
        
        generated_terrains = []
        
        for terrain_name in terrains_to_generate:
            if terrain_name not in terrain_configs:
                logger.warning(f"⚠️ Terrain inconnu: {terrain_name}")
                continue
                
            config = terrain_configs[terrain_name]
            seed = random.randint(1, 999999)  # Nouvelle seed aléatoire
            
            logger.info(f"🏔️ Génération {terrain_name} (seed={seed})...")
            
            # Prépare la commande
            cmd = [
                sys.executable, "-m", "terrain_gen.heightmap",
                "--size", str(config['size']),
                "--seed", str(seed),
                "--output", str(config['output']),
                "--ds-roughness", str(config.get('ds_roughness', 0.6)),
                "--fbm-octaves", str(config.get('fbm_octaves', 6)),
                "--blend-ratio", str(config.get('blend_ratio', 0.7))
            ]
            
            # Ajoute les paramètres optionnels
            if 'fbm_frequency' in config:
                cmd.extend(["--fbm-frequency", str(config['fbm_frequency'])])
            
            # Exécute la génération
            try:
                result = subprocess.run(
                    cmd,
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=120  # Timeout de 2 minutes pour les résolutions 16K
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ {terrain_name} généré avec succès")
                    
                    # Post-traitement spécial pour l'archipel
                    if config.get('post_process') == 'archipel':
                        apply_archipel_threshold(config['output'])
                    
                    generated_terrains.append({
                        'name': terrain_name,
                        'seed': seed,
                        'status': 'success'
                    })
                else:
                    logger.error(f"❌ Erreur génération {terrain_name}: {result.stderr}")
                    generated_terrains.append({
                        'name': terrain_name,
                        'status': 'error',
                        'error': result.stderr
                    })
                    
            except subprocess.TimeoutExpired:
                logger.error(f"⏰ Timeout génération {terrain_name}")
                generated_terrains.append({
                    'name': terrain_name,
                    'status': 'timeout'
                })
        
        return jsonify({
            'status': 'success',
            'message': f'Regénération terminée pour {len(generated_terrains)} terrains',
            'terrains': generated_terrains
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur API: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def apply_archipel_threshold(image_path):
    """Applique un seuillage pour créer des îles (post-traitement archipel)."""
    try:
        from PIL import Image
        import numpy as np
        
        # Charge l'image
        img = Image.open(image_path)
        data = np.array(img)
        
        # Applique le seuillage (comme dans example.py)
        threshold = 0.4 * 65535  # Conversion en 16-bit
        data = np.where(data > threshold, 
                       ((data - threshold) / (65535 - threshold) * 65535).astype(np.uint16), 
                       0)
        
        # Sauvegarde
        result_img = Image.fromarray(data, mode='I;16')
        result_img.save(image_path)
        
        logger.info(f"✅ Post-traitement archipel appliqué à {image_path}")
        
    except Exception as e:
        logger.error(f"❌ Erreur post-traitement archipel: {e}")

@app.route('/api/status', methods=['GET'])
def status():
    """Endpoint de statut pour vérifier que l'API fonctionne."""
    return jsonify({
        'status': 'ok',
        'message': 'API de regénération des terrains active'
    })

if __name__ == '__main__':
    # Crée le dossier de sortie si nécessaire
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    print("🚀 Démarrage de l'API de regénération des terrains...")
    print(f"📁 Dossier de sortie: {OUTPUT_PATH}")
    
    # Lance le serveur
    app.run(host='127.0.0.1', port=5001, debug=True) 