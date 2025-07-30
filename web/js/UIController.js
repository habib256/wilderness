/**
 * UIController - Gère l'interface utilisateur et les interactions
 */
class UIController {
    constructor(terrainLoader, terrainRenderer) {
        this.terrainLoader = terrainLoader;
        this.terrainRenderer = terrainRenderer;
        this.currentTerrainName = 'montagneux';

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
     * Initialise le sélecteur de terrain
     */
    initTerrainSelector() {
        const terrainButtons = document.querySelectorAll('.terrain-btn');
        
        terrainButtons.forEach(button => {
            button.addEventListener('click', async (event) => {
                const terrainName = event.target.dataset.terrain;
                
                if (terrainName && terrainName !== this.currentTerrainName) {
                    await this.switchTerrain(terrainName);
                }
            });
        });
    }

    /**
     * Initialise les contrôles de rendu
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

        // Position du soleil
        const sunPositionSlider = document.getElementById('sunPosition');
        const sunPositionValue = document.getElementById('sunPositionValue');
        
        sunPositionSlider.value = 180;
        sunPositionValue.textContent = this.getSunDirectionText(180);
        
        sunPositionSlider.addEventListener('input', (event) => {
            const angle = parseInt(event.target.value);
            sunPositionValue.textContent = this.getSunDirectionText(angle);
            
            this.terrainRenderer.updateSettings({
                sunPosition: angle
            });
        });

        // Qualité des ombres
        const shadowQualitySelect = document.getElementById('shadowQuality');
        shadowQualitySelect.addEventListener('change', (event) => {
            const quality = event.target.value;
            
            this.terrainRenderer.updateSettings({
                shadowQuality: quality
            });
            
            console.log(`🌫️ Qualité des ombres: ${quality}`);
        });

        // Gestion de la génération de depth map
        this.initDepthMapControls();

    }

    /**
     * Initialise les contrôles de génération de depth map
     */
    initDepthMapControls() {
        const generateBtn = document.getElementById('generateDepthMap');
        const downloadBtn = document.getElementById('downloadDepthMap');
        const closeBtn = document.getElementById('closeDepthMap');
        const previewDiv = document.getElementById('depthMapPreview');
        const canvas = document.getElementById('depthMapCanvas');

        // Bouton de génération
        generateBtn.addEventListener('click', async () => {
            try {
                generateBtn.disabled = true;
                generateBtn.textContent = '⏳ Génération...';
                
                console.log('📊 Début de génération de depth map...');
                
                // Génère la depth map
                const depthMapResult = this.terrainRenderer.generateDepthMap(512, 512);
                
                if (depthMapResult) {
                    // Affiche la preview
                    this.displayDepthMapPreview(depthMapResult);
                    console.log('✅ Depth map générée avec succès');
                } else {
                    console.error('❌ Échec de la génération de depth map');
                    alert('Erreur lors de la génération de la depth map');
                }
                
            } catch (error) {
                console.error('❌ Erreur lors de la génération:', error);
                alert('Erreur lors de la génération de la depth map');
            } finally {
                generateBtn.disabled = false;
                generateBtn.textContent = '📊 Générer Depth Map';
            }
        });

        // Bouton de téléchargement
        downloadBtn.addEventListener('click', () => {
            this.downloadDepthMap();
        });

        // Bouton de fermeture
        closeBtn.addEventListener('click', () => {
            previewDiv.style.display = 'none';
        });
    }

    /**
     * Affiche la preview de la depth map
     * @param {Object} depthMapResult - Résultat de la génération
     */
    displayDepthMapPreview(depthMapResult) {
        const previewDiv = document.getElementById('depthMapPreview');
        const canvas = document.getElementById('depthMapCanvas');
        const ctx = canvas.getContext('2d');

        // Configure la taille du canvas de preview
        canvas.width = 256;
        canvas.height = 256;

        // Dessine l'image de la depth map
        ctx.putImageData(depthMapResult.depthImage, 0, 0);

        // Affiche la preview
        previewDiv.style.display = 'block';

        // Stocke les données pour le téléchargement
        this.currentDepthMapData = depthMapResult;

        console.log(`📊 Preview affichée: ${depthMapResult.width}x${depthMapResult.height}`);
    }

    /**
     * Télécharge la depth map
     */
    downloadDepthMap() {
        if (!this.currentDepthMapData) {
            console.error('❌ Aucune depth map à télécharger');
            return;
        }

        try {
            // Crée un canvas temporaire pour l'export
            const canvas = document.createElement('canvas');
            canvas.width = this.currentDepthMapData.width;
            canvas.height = this.currentDepthMapData.height;
            const ctx = canvas.getContext('2d');

            // Dessine l'image complète
            ctx.putImageData(this.currentDepthMapData.depthImage, 0, 0);

            // Crée le lien de téléchargement
            const link = document.createElement('a');
            link.download = `depth_map_${Date.now()}.png`;
            link.href = canvas.toDataURL('image/png');

            // Déclenche le téléchargement
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            console.log('💾 Depth map téléchargée');

        } catch (error) {
            console.error('❌ Erreur lors du téléchargement:', error);
            alert('Erreur lors du téléchargement de la depth map');
        }
    }

    /**
     * Convertit un angle en description textuelle de moment de la journée
     * @param {number} angle - Angle en degrés (45-315, de l'aube au crépuscule)
     * @returns {string} Description du moment solaire
     */
    getSunDirectionText(angle) {
        // Plage limitée de l'aube au crépuscule (45°-315°)
        let timeText = '';
        if (angle >= 45 && angle < 75) timeText = 'Aube';
        else if (angle >= 75 && angle < 105) timeText = 'Lever (Est)';
        else if (angle >= 105 && angle < 135) timeText = 'Matinée';
        else if (angle >= 135 && angle < 165) timeText = 'Fin matinée';
        else if (angle >= 165 && angle < 195) timeText = 'Zénith (Midi)';
        else if (angle >= 195 && angle < 225) timeText = 'Début après-midi';
        else if (angle >= 225 && angle < 255) timeText = 'Après-midi';
        else if (angle >= 255 && angle < 285) timeText = 'Coucher (Ouest)';
        else if (angle >= 285 && angle <= 315) timeText = 'Crépuscule';
        else timeText = 'Zénith (Midi)'; // Valeur par défaut
        
        return timeText;
    }

    /**
     * Initialise l'affichage des statistiques
     */
    initStatsDisplay() {
        // Les statistiques seront mises à jour lors du changement de terrain
    }

    /**
     * Change de terrain
     */
    async switchTerrain(terrainName) {
        try {
            // Affiche le loading
            this.showLoading();

            // Désactive le bouton actuel
            this.setActiveTerrainButton(terrainName);

            // Charge le terrain
            console.log(`🔄 Changement vers terrain: ${terrainName}`);
            const terrainData = await this.terrainLoader.loadTerrain(terrainName);

            // Affiche le terrain en 3D
            this.terrainRenderer.displayTerrain(terrainData);
            this.terrainRenderer.currentTerrainData = terrainData;

            // Met à jour l'interface
            this.updateStats(terrainData);
            this.currentTerrainName = terrainName;

            // Cache le loading
            this.hideLoading();

            console.log(`✅ Terrain ${terrainName} chargé et affiché`);

        } catch (error) {
            console.error(`❌ Erreur changement terrain ${terrainName}:`, error);
            this.showError(`Erreur lors du chargement du terrain: ${error.message}`);
            this.hideLoading();
        }
    }

    /**
     * Met à jour l'affichage des statistiques
     */
    updateStats(terrainData) {
        const { stats } = terrainData;

        document.getElementById('stat-size').textContent = stats.size;
        document.getElementById('stat-min').textContent = stats.min.toFixed(4);
        document.getElementById('stat-max').textContent = stats.max.toFixed(4);
        document.getElementById('stat-mean').textContent = stats.mean.toFixed(4);
        document.getElementById('stat-roughness').textContent = stats.roughness.toFixed(4);
    }

    /**
     * Met à jour le bouton actif dans le sélecteur
     */
    setActiveTerrainButton(terrainName) {
        // Désactive tous les boutons
        document.querySelectorAll('.terrain-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        // Active le bouton sélectionné
        const activeButton = document.querySelector(`[data-terrain="${terrainName}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
    }

    /**
     * Affiche l'écran de chargement
     */
    showLoading() {
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            loadingDiv.classList.remove('hidden');
        }
    }

    /**
     * Cache l'écran de chargement
     */
    hideLoading() {
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            loadingDiv.classList.add('hidden');
        }
    }

    /**
     * Affiche une erreur
     */
    showError(message) {
        // Simple alert pour le moment - pourrait être amélioré avec une modal
        alert(`❌ ${message}`);
    }

    /**
     * Charge le terrain initial
     */
    async loadInitialTerrain() {
        try {
            console.log('🚀 Chargement du terrain initial...');
            await this.switchTerrain(this.currentTerrainName);
        } catch (error) {
            console.error('❌ Erreur chargement initial:', error);
            this.showError('Impossible de charger le terrain initial');
        }
    }

    /**
     * Précharge tous les terrains en arrière-plan
     */
    async preloadTerrains() {
        try {
            console.log('📦 Préchargement des terrains en arrière-plan...');
            
            // Lance le préchargement sans attendre
            setTimeout(async () => {
                try {
                    await this.terrainLoader.preloadAllTerrains();
                    console.log('✅ Préchargement terminé');
                } catch (error) {
                    console.warn('⚠️ Erreur préchargement:', error);
                }
            }, 100);

        } catch (error) {
            console.warn('⚠️ Erreur lancement préchargement:', error);
        }
    }

    /**
     * Met à jour les contrôles en temps réel
     */
    updateControls() {
        // Synchronise les valeurs affichées avec les paramètres actuels
        const { settings } = this.terrainRenderer;

        document.getElementById('heightScale').value = settings.heightScale;
        document.getElementById('heightScaleValue').textContent = settings.heightScale.toFixed(1);
        
        // Synchronise la position du soleil
        const sunPosition = settings.sunPosition || 180;
        document.getElementById('sunPosition').value = sunPosition;
        document.getElementById('sunPositionValue').textContent = this.getSunDirectionText(sunPosition);
        
        const colorModeSelect = document.getElementById('colorMode');
        if (colorModeSelect) {
            colorModeSelect.value = settings.colorMode || 'height';
        }
    }



    /**
     * Gestion des raccourcis clavier globaux
     */
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Évite les conflits avec les contrôles de la caméra
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'SELECT') {
                return;
            }

            switch (event.code) {
                case 'Digit1':
                    this.switchTerrain('montagneux');
                    break;
                case 'Digit2':
                    this.switchTerrain('vallonne');
                    break;
                case 'Digit3':
                    this.switchTerrain('archipel');
                    break;
                case 'Digit4':
                    this.switchTerrain('heightmap');
                    break;
                case 'Digit5':
                    this.switchTerrain('reunion');
                    break;
                case 'Digit6':
                    this.switchTerrain('honshu_kanto');
                    break;
                case 'KeyR':
                    // Reset camera
                    this.terrainRenderer.resetCamera();
                    console.log('📷 Caméra resetée via touche R');
                    break;
                case 'KeyW':
                    // Toggle wireframe
                    const wireframeCheckbox = document.getElementById('wireframe');
                    if (wireframeCheckbox) {
                        wireframeCheckbox.checked = !wireframeCheckbox.checked;
                        wireframeCheckbox.dispatchEvent(new Event('change'));
                    }
                    break;
                case 'KeyC':
                    // Cycle color modes
                    const colorModeSelect = document.getElementById('colorMode');
                    if (colorModeSelect) {
                        const options = colorModeSelect.options;
                        const currentIndex = colorModeSelect.selectedIndex;
                        const nextIndex = (currentIndex + 1) % options.length;
                        colorModeSelect.selectedIndex = nextIndex;
                        colorModeSelect.dispatchEvent(new Event('change'));
                    }
                    break;
            }
        });

        console.log('⌨️ Raccourcis clavier initialisés');
    }




} 