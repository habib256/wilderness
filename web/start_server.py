#!/usr/bin/env python3
"""
Script pour démarrer le serveur de développement complet :
- Serveur web statique (port 5500)
- API de regénération des terrains (port 5000)
"""

import subprocess
import threading
import time
import sys
from pathlib import Path
import http.server
import socketserver
import os

def start_static_server():
    """Démarre le serveur web statique."""
    web_dir = Path(__file__).parent
    os.chdir(web_dir)
    
    PORT = 5500
    Handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🌐 Serveur web démarré sur http://127.0.0.1:{PORT}")
        httpd.serve_forever()

def start_api_server():
    """Démarre l'API de regénération."""
    api_script = Path(__file__).parent / "regenerate_api.py"
    
    print("🚀 Démarrage de l'API de regénération...")
    subprocess.run([sys.executable, str(api_script)])

def main():
    """Démarre les deux serveurs en parallèle."""
    print("🏔️ Démarrage du serveur Wilderness Terrain Viewer...")
    
    # Démarre l'API en arrière-plan
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    
    # Attend un peu que l'API démarre
    time.sleep(2)
    
    print("\n" + "="*50)
    print("🎮 Wilderness Terrain Viewer - Serveur actif")
    print("="*50)
    print("🌐 Interface web: http://127.0.0.1:5500")
    print("🔧 API regénération: http://127.0.0.1:5001")
    print("="*50)
    print("Appuyez sur Ctrl+C pour arrêter")
    print("="*50 + "\n")
    
    try:
        # Démarre le serveur web (bloquant)
        start_static_server()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du serveur...")
        sys.exit(0)

if __name__ == "__main__":
    main() 