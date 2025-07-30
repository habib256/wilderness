# 🚀 Instructions Rapides - Wilderness Terrain Viewer 3D

## Accès Direct

**URL** : http://localhost:8000

Le serveur HTTP est déjà lancé en arrière-plan sur le port 8000.

## 🎮 Utilisation Immédiate

### 1. Ouvrir dans le Navigateur
```bash
# Linux
xdg-open http://localhost:8000

# macOS  
open http://localhost:8000

# Windows
start http://localhost:8000
```

### 2. Interface Principale
- **Panneau droit** : Contrôles et statistiques
- **Écran principal** : Rendu 3D interactif
- **Écran de chargement** : Se cache automatiquement

### 3. Navigation Terrain
- **Boutons terrain** : Clic pour changer de terrain
- **Chiffres 1-4** : Raccourcis clavier
- **Statistiques** : Mise à jour automatique

### 4. Contrôles 3D
- **Souris gauche + drag** : Rotation caméra
- **Molette** : Zoom in/out
- **Souris droite + drag** : Pan
- **R** : Reset position caméra

### 5. Options Rendu
- **Échelle altitude** : Slider pour ajuster le relief

## 🔧 Dépannage Express

### Erreur de Chargement
```bash
# Relancer le serveur si nécessaire
cd web/
python3 -m http.server 8000
```

### Console Debug
- **F12** : Ouvrir console développeur
- **Console** : Voir logs détaillés
- **Network** : Vérifier chargement images

### Performance Lente
1. Réduire l'échelle d'altitude
2. Fermer autres onglets WebGL
3. Redémarrer le navigateur si nécessaire

## ✨ Fonctionnalités Cachées

### Raccourcis Avancés
- **R** : Reset position caméra
- **Konami Code** : Mode easter egg 🌟

### Terrains Recommandés
1. **Standard** : Démarrage rapide (terrain par défaut)
2. **Montagneux** : Relief spectaculaire
3. **Archipel** : Îles bien définies 
4. **Vallonné** : Terrain équilibré

---

**Prêt à explorer vos terrains procéduraux en 3D !** 🏔️ 