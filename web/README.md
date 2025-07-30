# Wilderness Terrain Viewer 3D 🏔️

Visualiseur 3D interactif pour les heightmaps générées par le système Wilderness.

## 🎯 Fonctionnalités

### Rendu 3D
- **Rendu temps réel** avec Three.js
- **Éclairage dynamique** avec ombres
- **Matériaux PBR** selon l'altitude
- **Contrôles caméra** orbit intuitifs

### Terrains Disponibles
- 🏔️ **Montagneux** - Rugosité élevée, dominance Diamond-Square
- 🌊 **Vallonné** - Ondulations douces, mélange équilibré  
- 🏝️ **Archipel** - Îles créées par seuillage
- 🗻 **Standard** - Paramètres par défaut (terrain de démarrage)

### Contrôles Interactifs
- **Échelle d'altitude** - 0 à 30 (défaut: 20)
- **Statistiques temps réel** - Min/Max/Moyenne/Rugosité

## 🚀 Utilisation

### Lancement
```bash
# Depuis le dossier web/
python3 -m http.server 8000

# Ou avec Node.js
npx http-server -p 8000

# Puis ouvrir: http://localhost:8000
```

### Contrôles Souris
- **Clic gauche + drag** : Rotation caméra
- **Molette** : Zoom
- **Clic droit + drag** : Pan

### Raccourcis Clavier
- **R** : Reset caméra à position optimale
- **1-4** : Sélection directe des terrains

## 🏗️ Architecture

### Structure Fichiers
```
web/
├── index.html          # Page principale
├── css/
│   └── style.css       # Styles interface
├── js/
│   ├── main.js         # Point d'entrée
│   ├── TerrainLoader.js    # Chargement heightmaps
│   ├── TerrainRenderer.js  # Rendu 3D Three.js
│   └── UIController.js  # Interface utilisateur
└── README.md           # Cette documentation
```

### Classes Principales

#### `TerrainLoader`
- Charge les heightmaps PNG depuis `../output/`
- Convertit en données Float32 normalisées [0,1]
- Calcule statistiques (min/max/moyenne/rugosité)
- Cache les terrains chargés

#### `TerrainRenderer`
- Génère géométrie 3D à partir des heightmaps
- Applique matériaux selon le mode couleur
- Gère éclairage et ombres
- Optimise résolution selon performance GPU

#### `UIController`
- Interface de sélection des terrains
- Contrôles de rendu temps réel
- Affichage des statistiques
- Gestion des raccourcis clavier

## 🔧 Configuration

### Optimisation Performance
- **GPU intégré** : Résolution automatiquement réduite à 128
- **GPU dédié** : Résolution par défaut 256
- **Anti-aliasing** : Activé si supporté
- **Pixel ratio** : Limité à 2x pour éviter la surcharge

### Paramètres Avancés
```javascript
// Dans TerrainRenderer.js
this.settings = {
    heightScale: 20,       // Échelle altitude
    meshQuality: 'medium'  // Qualité de rendu
};
```

## 📊 Validation Qualité

### Métriques Calculées
- **Taille** : Résolution heightmap (ex: 256x256)
- **Min/Max** : Range d'altitude normalisée [0,1]
- **Moyenne** : Centre de masse du terrain
- **Rugosité** : Gradient moyen (mesure complexité)

### Tests Automatiques
- Vérification format PNG 16-bit
- Validation range de données
- Calcul cohérence statistique
- Performance GPU benchmark

## 🐛 Dépannage

### Erreurs Communes

**"WebGL non supporté"**
- Activer l'accélération matérielle
- Mettre à jour les drivers GPU
- Utiliser un navigateur récent (Chrome/Firefox)

**"Terrain ne se charge pas"**
- Vérifier présence des fichiers dans `../output/`
- Lancer depuis serveur HTTP (pas file://)
- Contrôler console JavaScript (F12)

**"Performance lente"**
- Changer vers mode "Niveaux de gris"
- Réduire l'échelle d'altitude
- Fermer autres onglets WebGL

### Mode Debug
```javascript
// Dans la console browser (F12)
console.log(terrainLoader.terrains);     // Terrains chargés
console.log(terrainRenderer.settings);   // Paramètres rendu
performance.mark('terrain-render');      // Profiling
```

## 🚀 Extensions Possibles

### Phase 2 Intégration
- Import heightmaps érodées (érosion hydraulique)
- Support textures 4K Stable Diffusion
- Export vers formats Godot (.escn, .tres)

### Fonctionnalités Avancées
- **Animation** : Interpolation entre terrains
- **Post-processing** : Bloom, fog, DOF
- **Réalité Virtuelle** : Support WebXR
- **Multi-threading** : Web Workers pour calculs

### Interface Étendue
- **Sauvegarde** : Export images/vidéos
- **Comparaison** : Vue côte-à-côte
- **Édition** : Modification heightmap interactive
- **Mesures** : Outils distance/altitude

## 📝 Licence

MIT License - Compatible avec le projet Wilderness principal.

## 🤝 Contribution

Pour contribuer au visualiseur :
1. Fork le dépôt principal
2. Développer dans `web/js/`  
3. Tester sur plusieurs navigateurs
4. Proposer Pull Request avec démo

---

*Wilderness Terrain Viewer 3D - Visualisation procédurale en temps réel* 🌍 