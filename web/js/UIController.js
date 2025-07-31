/**
 * UIController - Gère l'interface utilisateur et les interactions
 */
class UIController {
    constructor(terrainLoader, terrainRenderer) {
        this.terrainLoader = terrainLoader;
        this.terrainRenderer = terrainRenderer;
        this.currentTerrainName = 'heightmap';

        this.initUI();
    }

    /**
     * Initialise l'interface utilisateur
     */
    initUI() {
        this.initTerrainSelector();
        this.initRenderControls();
        this.initStatsDisplay();
        this.initKeyboardShortcuts();

        console.log('✅ UI Controller initialisé');
    }

    /**
     * Initialise le sélecteur de terrain (menu déroulant)
     */
    initTerrainSelector() {
        const terrainSelect = document.getElementById('terrainSelect');
        
        terrainSelect.addEventListener('change', async (event) => {
            const terrainName = event.target.value;
            
            if (terrainName && terrainName !== this.currentTerrainName) {
                await this.switchTerrain(terrainName);
            }
        });
    }

    /**
     * Initialise les contrôles de rendu simplifiés
     */
    initRenderControls() {
        // Échelle de hauteur
        const heightScaleSlider = document.getElementById('heightScale');
        const heightScaleValue = document.getElementById('heightScaleValue');
        
        heightScaleSlider.value = 20;
        heightScaleValue.textContent = '20';
        
        heightScaleSlider.addEventListener('input', (event) => {
            const value = parseInt(event.target.value);
            heightScaleValue.textContent = value;
            
            this.terrainRenderer.updateSettings({
                heightScale: value
            });
        });
    }

    /**
     * Initialise l'affichage des statistiques
     */
    initStatsDisplay() {
        // Les statistiques seront mises à jour automatiquement
        console.log('📊 Affichage des statistiques initialisé');
    }

    /**
     * Change de terrain
     */
    async switchTerrain(terrainName) {
        try {
            console.log(`🔄 Changement vers le terrain: ${terrainName}`);
            
            this.showLoading();
            
            // Charge le nouveau terrain
            const terrainData = await this.terrainLoader.loadTerrain(terrainName);
            
            if (terrainData) {
                // Met à jour le rendu
                this.terrainRenderer.displayTerrain(terrainData);
                
                // Met à jour les statistiques
                this.updateStats(terrainData);
                
                // Met à jour le terrain actuel
                this.currentTerrainName = terrainName;
                
                console.log(`✅ Terrain ${terrainName} chargé avec succès`);
            } else {
                console.error(`❌ Impossible de charger le terrain: ${terrainName}`);
                this.showError(`Terrain ${terrainName} non trouvé`);
            }
            
        } catch (error) {
            console.error('❌ Erreur lors du changement de terrain:', error);
            this.showError('Erreur lors du chargement du terrain');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Met à jour les statistiques affichées
     */
    updateStats(terrainData) {
        const { min, max, roughness } = terrainData.stats;
        
        // Met à jour les éléments d'interface
        const minElement = document.getElementById('stat-min');
        const maxElement = document.getElementById('stat-max');
        const roughnessElement = document.getElementById('stat-roughness');
        
        if (minElement) minElement.textContent = min.toFixed(3);
        if (maxElement) maxElement.textContent = max.toFixed(3);
        if (roughnessElement) roughnessElement.textContent = roughness.toFixed(4);
    }

    /**
     * Affiche l'écran de chargement
     */
    showLoading() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.classList.remove('hidden');
        }
    }

    /**
     * Cache l'écran de chargement
     */
    hideLoading() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.classList.add('hidden');
        }
    }

    /**
     * Affiche une erreur
     */
    showError(message) {
        console.error('❌ Erreur:', message);
        // Pour l'instant, on affiche juste dans la console
        // On pourrait ajouter une notification visuelle plus tard
    }

    /**
     * Charge le terrain initial
     */
    async loadInitialTerrain() {
        try {
            console.log('🚀 Chargement du terrain initial...');
            
            const terrainData = await this.terrainLoader.loadTerrain(this.currentTerrainName);
            
            if (terrainData) {
                this.terrainRenderer.displayTerrain(terrainData);
                this.updateStats(terrainData);
                console.log('✅ Terrain initial chargé');
            }
            
        } catch (error) {
            console.error('❌ Erreur lors du chargement initial:', error);
        }
    }

    /**
     * Initialise les raccourcis clavier
     */
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            switch (event.key) {
                case 'r':
                case 'R':
                    // Reset de la caméra
                    this.terrainRenderer.resetCamera();
                    console.log('🔄 Caméra réinitialisée');
                    break;
                    
                case 'h':
                case 'H':
                    // Aide
                    this.showHelp();
                    break;
            }
        });
        
        console.log('⌨️ Raccourcis clavier initialisés (R: Reset caméra, H: Aide)');
    }

    /**
     * Affiche l'aide
     */
    showHelp() {
        console.log(`
🎮 Wilderness Terrain Viewer - Aide
====================================
Contrôles souris:
- Clic gauche + drag: Rotation caméra
- Molette: Zoom in/out
- Clic droit + drag: Pan

Raccourcis clavier:
- R: Reset position caméra
- H: Afficher cette aide

Interface:
- Menu déroulant: Sélection du terrain
- Slider: Échelle d'altitude
- Statistiques: Altitude min/max et rugosité
        `);
    }
} 