/**
 * TerrainRenderer - Rendu 3D des terrains avec Three.js
 */
class TerrainRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.terrainMesh = null;
        this.animationId = null;
        
        // Paramètres de rendu
        this.settings = {
            heightScale: 20, // Valeur par défaut mise à jour
            resolution: 4096,
            meshQuality: 'high', // Qualité augmentée pour réduire le faceting
            sunPosition: 180, // Position du soleil en degrés (0=Nord, 90=Est, 180=Sud/Zénith, 270=Ouest)
            shadowQuality: 'medium', // 'low', 'medium', 'high' - qualité des ombres (réduit pour performances)
            adaptiveShadows: true, // Active l'adaptation automatique des paramètres d'ombres
            shadowSoftness: 3.0 // Facteur de douceur des ombres - valeur fixe PCF
        };
        
        // Référence au terrain actuel pour l'analyse de complexité
        this.currentTerrainData = null;

        // Référence à la lumière directionnelle pour la mise à jour dynamique
        this.directionalLight = null;
        
        // Soleil 3D pulsant
        this.sunMesh = null;
        this.sunPulseTime = 0;
        this.sunAnimationReady = false;

        this.init();
    }

    /**
     * Initialise le rendu 3D
     */
    init() {
        // Récupère le canvas existant
        const canvas = document.getElementById('canvas3d');
        if (!canvas) {
            throw new Error('Canvas #canvas3d introuvable');
        }

        // Initialise le renderer avec le canvas existant
        this.renderer = new THREE.WebGLRenderer({ 
            canvas: canvas,
            antialias: true,
            alpha: false
        });
        
        // Configuration du renderer optimisée pour les ombres
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x87CEEB, 1.0); // Bleu ciel
        
        // Configuration optimisée des ombres avec PCF Soft fixe
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap; // PCF Soft fixe (douceur 3.0)
        this.renderer.shadowMap.autoUpdate = true;
        
        // Options supplémentaires pour éliminer les artefacts
        this.renderer.physicallyCorrectLights = true;
        
        // Améliore le rendu général
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.0;
        
        // Optimisations de performance
        this.renderer.sortObjects = true;
        this.renderer.autoClear = true;

        console.log(`🖥️ Renderer initialisé: ${window.innerWidth}x${window.innerHeight}`);

        // Initialise la scène
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.Fog(0x87CEEB, 100, 1000);

        // Initialise la caméra
        this.camera = new THREE.PerspectiveCamera(
            75, 
            window.innerWidth / window.innerHeight, 
            0.1, 
            2000
        );
        this.camera.position.set(25, 25, 25);

        // Initialise les contrôles
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.maxDistance = 500;
        this.controls.minDistance = 5;

        // Éclairage initial
        this.setupLighting(100);

        // Événements
        window.addEventListener('resize', () => this.onWindowResize());
        
        // Lance le rendu
        this.animate();
        
        console.log('✅ Renderer 3D initialisé');
    }

    /**
     * Configure l'éclairage de la scène
     */
    setupLighting() {
        // Lumière ambiante réduite pour ombres très douces (cohérent avec shadowSoftness=3.0)
        const ambientLight = new THREE.AmbientLight(0x606060, 0.4);
        this.scene.add(ambientLight);

        // Lumière directionnelle principale (soleil)
        this.directionalLight = new THREE.DirectionalLight(0xffffff, 0.7);
        this.directionalLight.castShadow = true;
        
        // Configuration des ombres optimisée pour performance/qualité
        this.directionalLight.shadow.mapSize.width = 4096;   // Résolution optimisée 4K
        this.directionalLight.shadow.mapSize.height = 4096;
        this.directionalLight.shadow.camera.near = 0.1;
        this.directionalLight.shadow.camera.far = 800;
        
        // Bounds adaptatifs selon la position du soleil (mis à jour dans updateSunPosition)
        this.directionalLight.shadow.camera.left = -150;
        this.directionalLight.shadow.camera.right = 150;
        this.directionalLight.shadow.camera.top = 150;
        this.directionalLight.shadow.camera.bottom = -150;
        
        // Paramètres anti-aliasing avancés pour éliminer complètement les bandes
        this.directionalLight.shadow.bias = -0.00005;         // Valeur très douce de base
        this.directionalLight.shadow.normalBias = 0.008;      // Valeur très douce de base
        this.directionalLight.shadow.radius = 8;              // Flou plus important pour masquer les artefacts
        this.directionalLight.shadow.blurSamples = 50;        // Beaucoup plus d'échantillons
        
        // Protection avancée contre les artefacts de précision
        this.directionalLight.shadow.camera.matrixAutoUpdate = true;
        
        // Système de dithering temporel stable
        this.shadowDitherOffset = 0;
        this.ditherPattern = this.generateDitherPattern();
        this.frameCount = 0;

        this.scene.add(this.directionalLight);

        // Lumière de remplissage pour adoucir les ombres et améliorer le lissage
        const fillLight = new THREE.DirectionalLight(0x87CEEB, 0.3);
        fillLight.position.set(-80, 60, -60);
        this.scene.add(fillLight);

        // Création du soleil 3D pulsant
        this.createSun3D();
        
        // Application de la position initiale du soleil (après création du mesh 3D)
        this.updateSunPosition(this.settings.sunPosition);

        // Helper pour visualiser la lumière (debug)
        // const helper = new THREE.DirectionalLightHelper(this.directionalLight, 5);
        // this.scene.add(helper);
    }

    /**
     * Crée le soleil 3D pulsant
     */
    createSun3D() {
        try {
            // Vérifie que la scène est initialisée
            if (!this.scene) {
                console.warn('⚠️ Scene non initialisée, report de la création du soleil');
                return;
            }

            // Géométrie sphérique pour le soleil
            const sunGeometry = new THREE.SphereGeometry(8, 32, 16); // Rayon 8, 32 segments
            
            // Matériau émissif pour simuler la luminosité du soleil
            const sunMaterial = new THREE.MeshBasicMaterial({
                color: new THREE.Color(0xFFFF00), // Jaune de base
                emissive: new THREE.Color(0xFFAA00), // Émission orange
                emissiveIntensity: 0.8
            });
            
            // Création du mesh
            this.sunMesh = new THREE.Mesh(sunGeometry, sunMaterial);
            this.sunMesh.name = 'sun3D';
            
            // Le soleil ne projette pas d'ombres mais peut en recevoir (eclipse effet)
            this.sunMesh.castShadow = false;
            this.sunMesh.receiveShadow = false;
            
            // Ajoute le soleil à la scène
            this.scene.add(this.sunMesh);
            
            // Position initiale du soleil (appliquée immédiatement, avant même l'animation)
            this.applySunInitialPosition();
            
            // Active l'animation après un court délai pour s'assurer que tout est initialisé
            setTimeout(() => {
                this.sunAnimationReady = true;
                console.log('✅ Animation du soleil 3D activée');
            }, 100);
            
            console.log('☀️ Soleil 3D créé et ajouté à la scène avec position initiale');
        } catch (error) {
            console.error('❌ Erreur lors de la création du soleil 3D:', error);
        }
    }

    /**
     * Applique la position initiale du soleil immédiatement après sa création
     */
    applySunInitialPosition() {
        if (!this.sunMesh || !this.directionalLight) {
            return;
        }

        const angle = this.settings.sunPosition;
        
        // TRAJECTOIRE RÉALISTE : Remappe l'angle du slider (0-360°) vers une trajectoire Est-Ouest (60-300°)
        const realAngle = 60 + (angle / 360) * 240; // Mappe 0-360° vers 60-300° (240° d'arc réaliste)
        const realAngleRad = (realAngle * Math.PI) / 180;
        
        // Distance horizontale du soleil  
        const distance = 150;
        
        // HAUTEUR RÉALISTE : Calcule la hauteur selon un arc de cercle naturel
        const sunArcProgress = (realAngle - 60) / 240; // Progression de 0 à 1 sur l'arc Est-Ouest
        const sunElevationAngle = Math.sin(sunArcProgress * Math.PI); // Sinusoïde parfaite 0->1->0
        
        // Hauteur : 15 unités à l'horizon (aube/crépuscule) à 140 unités au zénith (midi)
        const minHorizonHeight = 15;
        const maxZenithHeight = 140;
        let baseHeight = minHorizonHeight + sunElevationAngle * (maxZenithHeight - minHorizonHeight);
        
        // Contrainte physique : le soleil ne peut pas descendre trop bas
        const minSunHeight = 8; // 8 unités minimum au-dessus du sol 
        const height = Math.max(baseHeight, minSunHeight);
        
        // Position X et Z selon l'angle réel (trajectoire naturelle Est-Ouest)
        const x = Math.sin(realAngleRad) * distance;
        const z = Math.cos(realAngleRad) * distance;
        
        // Applique la position directement sur le mesh du soleil
        this.sunMesh.position.set(x, height, z);
        
        console.log(`🌅 Position initiale soleil: ${angle}°→${realAngle.toFixed(1)}°réel (${x.toFixed(1)}, ${height.toFixed(1)}, ${z.toFixed(1)})`);
    }

    /**
     * Met à jour la position du soleil selon l'angle en degrés avec trajectoire réaliste
     * @param {number} angle - Angle en degrés (remappé pour trajectoire Est-Ouest réaliste)
     */
    updateSunPosition(angle) {
        if (!this.directionalLight) {
            return;
        }

        // TRAJECTOIRE RÉALISTE : Remappe l'angle du slider (0-360°) vers une trajectoire Est-Ouest (60-300°)
        // 0° du slider = 60° réel (aube à l'est-nord-est)
        // 180° du slider = 180° réel (midi au sud) - ZÉNITH MAXIMUM
        // 360° du slider = 300° réel (crépuscule à l'ouest-nord-ouest)
        const realAngle = 60 + (angle / 360) * 240; // Mappe 0-360° vers 60-300° (240° d'arc réaliste)
        const realAngleRad = (realAngle * Math.PI) / 180;
        
        // Distance horizontale du soleil  
        const distance = 150;
        
        // HAUTEUR RÉALISTE : Calcule la hauteur selon un arc de cercle naturel
        // Le soleil atteint son zénith maximum au sud (180°) et descend vers les horizons
        const sunArcProgress = (realAngle - 60) / 240; // Progression de 0 à 1 sur l'arc Est-Ouest
        const sunElevationAngle = Math.sin(sunArcProgress * Math.PI); // Sinusoïde parfaite 0->1->0
        
        // Hauteur : 15 unités à l'horizon (aube/crépuscule) à 140 unités au zénith (midi)
        const minHorizonHeight = 15;
        const maxZenithHeight = 140;
        let baseHeight = minHorizonHeight + sunElevationAngle * (maxZenithHeight - minHorizonHeight);
        
        // Contrainte physique : le soleil ne peut pas descendre trop bas
        const minSunHeight = 8; // 8 unités minimum au-dessus du sol 
        const height = Math.max(baseHeight, minSunHeight);
        
        // Position X et Z selon l'angle réel (trajectoire naturelle Est-Ouest)
        const x = Math.sin(realAngleRad) * distance;
        const z = Math.cos(realAngleRad) * distance;
        
        this.directionalLight.position.set(x, height, z);
        
        // Met à jour la position du soleil 3D pour qu'il suive la lumière
        if (this.sunMesh) {
            this.sunMesh.position.set(x, height, z);
        }
        
        // Ajuste l'intensité selon la hauteur réaliste (plus faible à l'aube/crépuscule)
        const maxIntensity = 0.8;
        const minIntensity = 0.3;
        // Utilise l'angle d'élévation pour un calcul plus naturel de l'intensité
        const intensity = minIntensity + (maxIntensity - minIntensity) * sunElevationAngle;
        this.directionalLight.intensity = intensity;
        
        // Ajuste les paramètres d'ombres selon la position du soleil
        this.updateShadowParameters(realAngle, height);
        
        // Couleurs réalistes selon la position du soleil dans son arc
        if (sunElevationAngle < 0.3) {
            // Horizons (aube/crépuscule) : lumière très dorée/orangée
            this.directionalLight.color.setHex(0xFF9944);
        } else if (sunElevationAngle < 0.6) {
            // Matin/après-midi : lumière légèrement chaude
            this.directionalLight.color.setHex(0xFFDD88);
        } else {
            // Zénith (midi) : lumière blanche pure
            this.directionalLight.color.setHex(0xFFFFFF);
        }
        
        // Stocke l'angle pour référence
        this.settings.sunPosition = angle;
        
        console.log(`☀️ Position soleil: ${angle}°→${realAngle.toFixed(1)}°réel (${x.toFixed(1)}, ${height.toFixed(1)}, ${z.toFixed(1)}) élévation=${(sunElevationAngle*100).toFixed(0)}% intensité=${intensity.toFixed(2)}`);
    }

    /**
     * Met à jour les paramètres d'ombres selon la position du soleil
     * @param {number} angle - Angle du soleil en degrés
     * @param {number} height - Hauteur du soleil
     */
    updateShadowParameters(angle, height) {
        if (!this.directionalLight || !this.directionalLight.shadow) {
            return;
        }

        const shadow = this.directionalLight.shadow;
        
        // Ajuste les bounds de la shadow camera de manière plus précise
        const heightFactor = Math.max(0.3, height / 120); // Facteur basé sur la hauteur (0.3 à 1.0)
        const baseBound = 120;
        
        // Calcule l'extension directionnelle selon l'angle du soleil
        const angleRad = (angle * Math.PI) / 180;
        
        // Extension plus intelligente selon l'angle et la hauteur
        const heightMultiplier = 1 + (2 * (1 - heightFactor)); // Plus d'extension quand le soleil est bas
        const extendX = Math.abs(Math.sin(angleRad)) * 60 * heightMultiplier;
        const extendZ = Math.abs(Math.cos(angleRad)) * 60 * heightMultiplier;
        
        // Bounds adaptatifs avec marge supplémentaire pour les angles extrêmes
        const marginX = height < 50 ? 30 : 10; // Marge supplémentaire pour angles extrêmes
        const marginZ = height < 50 ? 30 : 10;
        
        shadow.camera.left = -(baseBound + extendX + marginX);
        shadow.camera.right = baseBound + extendX + marginX;
        shadow.camera.top = baseBound + extendZ + marginZ;
        shadow.camera.bottom = -(baseBound + extendZ + marginZ);
        
        // Ajuste la distance near/far pour éviter le z-fighting
        shadow.camera.near = height < 40 ? 0.05 : 0.1;
        shadow.camera.far = 1000;
        
        // Ajuste le bias de manière progressive pour éliminer les artefacts
        const minHeightRef = 30; // Référence minimale fixe
        const heightNormalized = Math.max(0, Math.min(1, (height - minHeightRef) / (120 - minHeightRef))); // Normalise entre référence et zénith
        
        // Détection multi-niveaux des angles problématiques
        const isExtremeAngle = height < 50;
        const isCriticalAngle = height < 35;
        const angleFactor = Math.abs(Math.sin((angle - 180) * Math.PI / 180)); // 0 au sud, 1 à l'est/ouest
        const isEdgeCase = height <= 12 && angleFactor > 0.9; // Angles très bas
        
        // Bias adaptatif avec correction spéciale pour cas extrêmes
        let baseBias = -0.0001;
        let normalBias = 0.01;
        let radius = 4;
        
        // Système de bias adaptatif intelligent basé sur angle et distance
        const biasConfig = this.calculateSmartBias(angle, height, angleFactor, heightNormalized, isEdgeCase, isCriticalAngle, isExtremeAngle);
        
        baseBias = biasConfig.bias;
        normalBias = biasConfig.normalBias;
        radius = biasConfig.radius;
        
        shadow.bias = baseBias;
        shadow.normalBias = normalBias;
        
        // Applique le facteur de douceur utilisateur APRÈS le calcul adaptatif
        const userSoftnessFactor = this.settings.shadowSoftness || 1.0;
        
        // Plages de valeurs plus larges pour rendre les changements plus visibles
        const minRadius = 2;
        const maxRadius = 25; // Augmenté de 15 à 25
        shadow.radius = Math.min(maxRadius, Math.max(minRadius, radius * userSoftnessFactor));
        
        // Applique aussi le facteur aux échantillons de flou avec une plage plus large
        const minSamples = 8;
        const maxSamples = 100; // Augmenté de 50 à 100
        const baseSamples = 30; // Augmenté de 25 à 30
        shadow.blurSamples = Math.max(minSamples, Math.min(maxSamples, Math.floor(baseSamples * userSoftnessFactor)));
        
        // Force la mise à jour de la shadow camera
        shadow.camera.updateProjectionMatrix();
        
        // Log détaillé pour debug des artefacts avec classification précise
        const totalBound = baseBound + Math.max(extendX, extendZ) + Math.max(marginX, marginZ);
        let debugInfo = '[NORMAL]';
        if (isEdgeCase) debugInfo = '[CRITIQUE]';
        else if (isCriticalAngle) debugInfo = '[TRÈS EXTRÊME]';
        else if (isExtremeAngle) debugInfo = '[EXTRÊME]';
        
        console.log(`🌫️ Ombres${debugInfo}: angle=${angle.toFixed(0)}°, h=${height.toFixed(0)}, bounds=±${totalBound.toFixed(0)}, bias=${shadow.bias.toFixed(5)}, normalBias=${shadow.normalBias.toFixed(3)}, radius=${shadow.radius.toFixed(1)}, samples=${shadow.blurSamples}, softness=${userSoftnessFactor.toFixed(1)} (${this.getShadowMapTypeName()})`);
        
        // Protection supplémentaire contre les artefacts persistants
        if (isEdgeCase || (isExtremeAngle && angleFactor > 0.85)) {
            // Force une mise à jour complète pour les cas les plus problématiques
            shadow.camera.updateMatrixWorld(true);
            shadow.camera.updateWorldMatrix(true, false);
            
            // Dithering temporel stable pour éliminer les bandes régulières
            const ditherOffset = this.getTemporalDither();
            this.directionalLight.position.x += ditherOffset.x;
            this.directionalLight.position.z += ditherOffset.z;
            
            console.log(`⚠️ Protection renforcée appliquée pour angle problématique: ${angle.toFixed(0)}°`);
        }
    }

    /**
     * Met à jour l'animation de pulsation du soleil 3D
     */
    updateSunPulsing() {
        // Vérifications de sécurité
        if (!this.sunAnimationReady || !this.sunMesh || !this.sunMesh.material || !this.sunMesh.material.color || !this.sunMesh.material.emissive) {
            return;
        }

        // Incrémente le temps de pulsation
        this.sunPulseTime += 0.02; // Vitesse de pulsation

        // Calcul de la pulsation (oscillation entre 0.5 et 1.5)
        const pulseIntensity = 1.0 + 0.5 * Math.sin(this.sunPulseTime);
        
        // Calcul de la couleur pulsante (rouge -> jaune -> rouge)
        const colorPhase = (Math.sin(this.sunPulseTime * 0.7) + 1) / 2; // 0 à 1
        
        // Interpolation rouge (1,0,0) vers jaune (1,1,0)
        const red = 1.0;
        const green = colorPhase;
        const blue = 0.0;
        
        // Application de la couleur et de l'intensité avec vérifications
        try {
            this.sunMesh.material.color.setRGB(red, green, blue);
            this.sunMesh.material.emissive.setRGB(red * 0.8, green * 0.6, blue * 0.2);
            this.sunMesh.material.emissiveIntensity = pulseIntensity;
            
            // Légère variation de taille pour accentuer la pulsation
            const scaleVariation = 1.0 + 0.1 * Math.sin(this.sunPulseTime * 1.3);
            this.sunMesh.scale.setScalar(scaleVariation);
        } catch (error) {
            console.warn('⚠️ Erreur lors de la mise à jour de la pulsation du soleil:', error);
        }
    }

    /**
     * Ajoute une grille de référence
     */
    addGrid() {
        const gridHelper = new THREE.GridHelper(100, 20, 0x888888, 0x444444);
        gridHelper.position.y = -0.1;
        this.scene.add(gridHelper);
    }

    /**
     * Ajoute un cube de test pour vérifier le rendu
     */
    addTestCube() {
        const geometry = new THREE.BoxGeometry(10, 10, 10);
        const material = new THREE.MeshLambertMaterial({ color: 0xff0000 });
        this.testCube = new THREE.Mesh(geometry, material);
        this.testCube.position.set(0, 5, 0);
        this.scene.add(this.testCube);
        console.log('🎲 Cube de test ajouté');
    }

    /**
     * Supprime le cube de test
     */
    removeTestCube() {
        if (this.testCube) {
            this.scene.remove(this.testCube);
            this.testCube.geometry.dispose();
            this.testCube.material.dispose();
            this.testCube = null;
            console.log('🎲 Cube de test supprimé');
        }
    }

    /**
     * Positionne la caméra pour une vue optimale du terrain
     */
    resetCamera(size = 100) {
        if (!this.camera) return;
        
        // Position optimisée pour une vue plus proche du terrain
        const distance = 150; // Distance réduite pour une vue plus proche
        this.camera.position.set(distance, distance * 0.8, distance);
        this.camera.lookAt(0, 25, 0); // Regarde légèrement au-dessus du sol
        
        // Ajuste les paramètres de la caméra
        this.camera.near = 0.1;
        this.camera.far = 5000;
        this.camera.updateProjectionMatrix();
        
        if (this.controls) {
            this.controls.target.set(0, 25, 0); // Centre sur le terrain avec hauteur
            this.controls.update();
        }
        
        console.log(`📷 Caméra: pos(${this.camera.position.x}, ${this.camera.position.y}, ${this.camera.position.z})`);
        console.log(`📷 Caméra: near=${this.camera.near}, far=${this.camera.far}`);
    }



    /**
     * Calcule la résolution des segments basée sur la qualité
     */
    getSegmentResolution(width, height) {
        const qualityLimits = {
            'low': 128,
            'medium': 256, 
            'high': 512,
            'ultra': 1024,
            'extreme': 2048
        };
        
        const maxSegments = qualityLimits[this.settings.meshQuality] || 256;
        const segmentsX = Math.min(maxSegments, width - 1);
        const segmentsY = Math.min(maxSegments, height - 1);
        

        
        console.log(`🎯 Qualité ${this.settings.meshQuality}: ${segmentsX}x${segmentsY} segments (limite: ${maxSegments})`);
        
        return { segmentsX, segmentsY };
    }

    /**
     * Génère la géométrie 3D du terrain à partir des données de hauteur
     */
    generateTerrainGeometry(terrainData) {
        const { width, height, heightData } = terrainData;
        
        console.log(`🔧 Génération géométrie pour ${width}x${height} heightmap`);
        
        // Utilise la résolution adaptative basée sur la qualité détectée
        const { segmentsX, segmentsY } = this.getSegmentResolution(width, height);
        
        console.log(`📐 Créé géométrie ${segmentsX}x${segmentsY} segments`);
        
        // Crée la géométrie manuellement pour être sûr qu'elle soit correcte
        const geometry = new THREE.BufferGeometry();
        
        // Calcule le nombre de vertices et faces
        const verticesCount = (segmentsX + 1) * (segmentsY + 1);
        const facesCount = segmentsX * segmentsY * 2; // 2 triangles par carré
        
        console.log(`📊 ${verticesCount} vertices, ${facesCount} triangles`);
        
        // Arrays pour les données
        const vertices = new Float32Array(verticesCount * 3);
        const indices = new Uint32Array(facesCount * 3);
        const uvs = new Float32Array(verticesCount * 2);
        
        // Génère les vertices
        let vertexIndex = 0;
        const heightScale = this.settings.heightScale;
        
        for (let y = 0; y <= segmentsY; y++) {
            for (let x = 0; x <= segmentsX; x++) {
                // Position dans l'espace 3D
                const posX = (x / segmentsX - 0.5) * 200; // [-100, 100]
                const posZ = (y / segmentsY - 0.5) * 200; // [-100, 100]
                // Mapping vers heightmap et UV (inversion X uniquement)
                const imgX = Math.floor(((segmentsX - x) / segmentsX) * (width - 1)); // <-- inversion X
                const imgY = Math.floor(((segmentsY - y) / segmentsY) * (height - 1));
                const clampedX = Math.max(0, Math.min(width - 1, imgX));
                const clampedY = Math.max(0, Math.min(height - 1, imgY));
                const heightIndex = clampedY * width + clampedX;
                let heightValue = heightData[heightIndex] || 0;
                
                // Note: Les terrains réels sont déjà normalisés correctement par leur post-traitement
                // Mer: [-0.1, 0], Terre: [0, 1], pas besoin d'inversion
                // if (terrainData.isRealTerrain) {
                //     heightValue = 1.0 - heightValue; // REMOVED: Inversion inappropriée
                // }
                
                const posY = heightValue * heightScale;
                // Stocke le vertex
                vertices[vertexIndex * 3] = posX;
                vertices[vertexIndex * 3 + 1] = posY;
                vertices[vertexIndex * 3 + 2] = posZ;
                // UV coordinates (inversion X uniquement)
                uvs[vertexIndex * 2] = 1 - (x / segmentsX);
                uvs[vertexIndex * 2 + 1] = 1 - (y / segmentsY);
                vertexIndex++;
            }
        }
        
        // Génère les indices pour les triangles
        let indexCount = 0;
        for (let y = 0; y < segmentsY; y++) {
            for (let x = 0; x < segmentsX; x++) {
                const a = y * (segmentsX + 1) + x;
                const b = y * (segmentsX + 1) + x + 1;
                const c = (y + 1) * (segmentsX + 1) + x;
                const d = (y + 1) * (segmentsX + 1) + x + 1;
                
                // Premier triangle
                indices[indexCount * 3] = a;
                indices[indexCount * 3 + 1] = b;
                indices[indexCount * 3 + 2] = c;
                indexCount++;
                
                // Deuxième triangle
                indices[indexCount * 3] = b;
                indices[indexCount * 3 + 1] = d;
                indices[indexCount * 3 + 2] = c;
                indexCount++;
            }
        }
        
        // Assigne les données à la géométrie
        geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
        geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
        geometry.setIndex(new THREE.BufferAttribute(indices, 1));
        
        // Calcule les normales
        geometry.computeVertexNormals();
        geometry.computeBoundingBox();
        geometry.computeBoundingSphere();
        
        console.log(`✅ Géométrie générée avec ${vertexIndex} vertices et ${indexCount} triangles`);
        console.log(`📦 Bounding box: min(${geometry.boundingBox.min.x.toFixed(1)}, ${geometry.boundingBox.min.y.toFixed(1)}, ${geometry.boundingBox.min.z.toFixed(1)}) max(${geometry.boundingBox.max.x.toFixed(1)}, ${geometry.boundingBox.max.y.toFixed(1)}, ${geometry.boundingBox.max.z.toFixed(1)})`);
        
        return geometry;
    }

    /**
     * Génère le matériau du terrain selon le mode de rendu
     */
    generateTerrainMaterial(terrainData) {
        // Mode normal - utilise MeshBasicMaterial pour être sûr qu'il soit visible
        const { width, height, heightData } = terrainData;
        
        // Crée une texture basée sur l'altitude
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        const imageData = ctx.createImageData(width, height);
        const data = imageData.data;
        
        const heightScale = this.settings.heightScale;
        
        // Génère la texture d'altitude
        const isRealTerrain = this.currentTerrainData && this.currentTerrainData.isRealTerrain;
        let minAlt = Infinity, maxAlt = -Infinity;
        for (let i = 0; i < heightData.length; i++) {
            let rawHeight = heightData[i];
            // Note: Terrains réels déjà normalisés par post-traitement
            // if (isRealTerrain) {
            //     rawHeight = 1.0 - rawHeight; // REMOVED: Inversion inappropriée
            // }
            const alt = rawHeight * heightScale;
            if (alt < minAlt) minAlt = alt;
            if (alt > maxAlt) maxAlt = alt;
        }
        const altRange = maxAlt - minAlt || 1;
        for (let i = 0; i < heightData.length; i++) {
            // Hauteur réelle - INVERSION pour terrain réel si nécessaire
            let rawHeight = heightData[i];
            
            // Note: Terrains réels déjà normalisés (mer: valeurs négatives, terre: valeurs positives)
            // if (isRealTerrain) {
            //     rawHeight = 1.0 - rawHeight; // REMOVED: Inversion inappropriée  
            // }
            
            const alt = rawHeight * heightScale;
            // Normalisation par rapport à l'altitude réelle affichée
            const h = (alt - minAlt) / altRange;
            let r, g, b;
            
            // DÉTECTION MER BASÉE SUR ALTITUDE RÉELLE POUR TERRAINS NORMALISÉS
            // Pour les terrains réels: valeurs négatives = mer, valeurs positives = terre
            const isSeaLevel = isRealTerrain ? (rawHeight <= 0.0) : (alt <= maxAlt * 0.01);
            const sandThreshold = isRealTerrain ? 0.05 : (maxAlt * 0.02); // Zone côtière
            
            // Si c'est de la mer (altitude <= 0 pour terrains réels) → BLEU OCÉAN
            if (isSeaLevel) {
                // Bleu océan profond - couleur plus réaliste pour la mer
                r = 0;
                g = 119;
                b = 190;
            } else if (isRealTerrain ? (rawHeight <= sandThreshold) : (alt <= sandThreshold)) {
                // Transition eau → sable (bleu océan → jaune sable)
                const transitionValue = isRealTerrain ? rawHeight : alt;
                const transitionMin = isRealTerrain ? 0.0 : (maxAlt * 0.01);
                const t = Math.max(0, Math.min(1, (transitionValue - transitionMin) / (sandThreshold - transitionMin)));
                r = Math.round(0 * (1 - t) + 238 * t);      // De bleu océan vers jaune sable
                g = Math.round(119 * (1 - t) + 203 * t);    // De bleu océan vers jaune sable
                b = Math.round(190 * (1 - t) + 173 * t);    // De bleu océan vers beige sable
            } else if (h < 0.35) {
                // Transition sable → herbe élargie (jaune sable → vert prairie)
                const sandLevelNormalized = isRealTerrain ? 
                    ((sandThreshold * heightScale) - minAlt) / altRange : 
                    (sandThreshold - minAlt) / altRange;
                const t = Math.max(0, Math.min(1, (h - sandLevelNormalized) / (0.35 - sandLevelNormalized)));
                r = Math.round(238 * (1 - t) + 34 * t);     // Sable vers vert prairie
                g = Math.round(203 * (1 - t) + 139 * t);    // Sable vers vert prairie
                b = Math.round(173 * (1 - t) + 34 * t);     // Beige vers vert prairie
            } else if (h < 0.85) {
                // Vert vers marron avec transition plus douce
                const t = Math.max(0, Math.min(1, (h - 0.35) / 0.5));  // Zone étendue et lissée
                r = Math.round(34 * (1 - t) + 101 * t);
                g = Math.round(139 * (1 - t) + 67 * t);
                b = Math.round(34 * (1 - t) + 33 * t);
            } else {
                // Marron vers blanc (neige) avec transition plus douce
                const t = Math.max(0, Math.min(1, (h - 0.85) / 0.15));  // Zone élargie
                r = Math.round(101 * (1 - t) + 255 * t);
                g = Math.round(67 * (1 - t) + 255 * t);
                b = Math.round(33 * (1 - t) + 255 * t);
            }
            const pixelIndex = i * 4;
            data[pixelIndex] = r;
            data[pixelIndex + 1] = g;
            data[pixelIndex + 2] = b;
            data[pixelIndex + 3] = 255;
        }
        
        ctx.putImageData(imageData, 0, 0);
        
        // Techniques avancées pour éliminer les bandes de couleur
        
        // 1. Dithering des couleurs pour briser les paliers
        const ditheredImageData = ctx.createImageData(width, height);
        const ditheredData = ditheredImageData.data;
        
        for (let i = 0; i < data.length; i += 4) {
            const ditherNoise = (Math.random() - 0.5) * 4; // Bruit léger
            ditheredData[i] = Math.max(0, Math.min(255, data[i] + ditherNoise));     // R
            ditheredData[i + 1] = Math.max(0, Math.min(255, data[i + 1] + ditherNoise)); // G
            ditheredData[i + 2] = Math.max(0, Math.min(255, data[i + 2] + ditherNoise)); // B
            ditheredData[i + 3] = data[i + 3]; // A
        }
        
        ctx.putImageData(ditheredImageData, 0, 0);
        
        // 2. Lissage multi-passes pour adoucir davantage
        ctx.filter = 'blur(0.8px)';
        ctx.drawImage(canvas, 0, 0);
        ctx.filter = 'blur(0.3px)';
        ctx.drawImage(canvas, 0, 0);
        ctx.filter = 'none';
        
        // Flip le canvas en Y pour matcher l'origine de la géométrie (origine en bas)
        ctx.save();
        ctx.translate(0, height);
        ctx.scale(1, -1);
        ctx.drawImage(canvas, 0, 0);
        ctx.restore();
        
        // Crée la texture Three.js avec un meilleur filtrage
        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.ClampToEdgeWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        texture.minFilter = THREE.LinearMipmapLinearFilter; // Meilleur filtrage pour réduire les artefacts
        texture.magFilter = THREE.LinearFilter;
        texture.generateMipmaps = true; // Active les mipmaps pour un rendu plus lisse
        
        // Utilise MeshLambertMaterial pour un éclairage doux et un rendu lissé
        return new THREE.MeshLambertMaterial({
            map: texture,
            side: THREE.DoubleSide, // IMPORTANT: Affiche les deux faces
            flatShading: false // IMPORTANT: Active l'interpolation des normales pour un rendu lissé
        });
    }

    /**
     * Affiche un terrain en 3D
     */
    displayTerrain(terrainData, resetCameraPosition = true) {
        console.log(`🎨 Affichage terrain: ${terrainData.name}`);
        
        // Stocke la référence au terrain pour l'analyse de complexité
        this.currentTerrainData = terrainData;
        
        // Supprime l'ancien terrain
        if (this.terrainMesh) {
            this.scene.remove(this.terrainMesh);
            this.terrainMesh.geometry.dispose();
            this.terrainMesh.material.dispose();
        }
        
        // Nettoie la scène (garde seulement les lumières et le soleil 3D)
        this.scene.children = this.scene.children.filter(child => 
            child.type === 'DirectionalLight' || child.type === 'AmbientLight' || child.name === 'sun3D'
        );
        
        // Ajoute une grille de référence discrète
        const gridHelper = new THREE.GridHelper(300, 30, 0x333333, 0x333333);
        gridHelper.material.opacity = 0.3;
        gridHelper.material.transparent = true;
        this.scene.add(gridHelper);
        console.log('�� Grille ajoutée');
        // Ajoute un repère d'axes XYZ à l'origine
        const axesHelper = new THREE.AxesHelper(100);
        this.scene.add(axesHelper);
        console.log('🧭 Repère XYZ ajouté');
        
        // Génère la géométrie et le matériau du terrain principal
        const geometry = this.generateTerrainGeometry(terrainData);
        const material = this.generateTerrainMaterial(terrainData);
        
        console.log(`🔧 Géométrie créée: ${geometry.attributes.position.count} vertices`);
        console.log(`🎨 Matériau créé: ${material.type}`);
        
        // Crée le mesh du terrain principal avec optimisation des ombres
        this.terrainMesh = new THREE.Mesh(geometry, material);
        this.terrainMesh.position.set(0, 0, 0); // Centré sur l'origine
        this.terrainMesh.receiveShadow = true;
        this.terrainMesh.castShadow = true;
        
        // Force la mise à jour des matrices pour un meilleur shadow mapping
        this.terrainMesh.matrixAutoUpdate = true;
        this.terrainMesh.frustumCulled = false; // Évite le culling prématuré pour les ombres
        
        this.scene.add(this.terrainMesh);
        
        console.log(`✅ Mesh ajouté: visible=${this.terrainMesh.visible}, position=(${this.terrainMesh.position.x}, ${this.terrainMesh.position.y}, ${this.terrainMesh.position.z})`);
        
        // Configure la caméra (seulement si demandé)
        if (resetCameraPosition) {
            this.resetCamera();
        }
        
        // Ré-applique la position du soleil pour s'assurer qu'elle reste correcte après le chargement
        if (this.sunMesh) {
            this.updateSunPosition(this.settings.sunPosition);
            console.log('☀️ Position du soleil ré-appliquée après chargement du terrain');
        }
        
        // Force un rendu immédiat
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
            console.log('🎬 Rendu forcé');
        }
        
        console.log(`✅ Terrain ${terrainData.name} affiché`);
    }

    /**
     * Met à jour les paramètres de rendu
     */
    updateSettings(newSettings) {
        Object.assign(this.settings, newSettings);
        
        // Met à jour la position du soleil si elle a changé
        if (newSettings.sunPosition !== undefined) {
            this.updateSunPosition(newSettings.sunPosition);
        }
        
        // Met à jour la qualité des ombres si elle a changé
        if (newSettings.shadowQuality !== undefined) {
            this.updateShadowQuality(newSettings.shadowQuality);
        }
        
        // Douceur des ombres fixe à 3.0 - pas de mise à jour dynamique
        
        // Recharge le terrain si nécessaire (sans reset de caméra)
        if (this.currentTerrainData && newSettings.heightScale !== undefined) {
            this.displayTerrain(this.currentTerrainData, false);
        }
    }

    /**
     * Met à jour la qualité des ombres
     */
    updateShadowQuality(quality) {
        if (!this.directionalLight || !this.directionalLight.shadow) {
            return;
        }

        const qualitySettings = {
            'low': 1024,
            'medium': 4096,
            'high': 8192,
            'ultra': 16384
        };

        const resolution = qualitySettings[quality] || 4096;
        
        // Met à jour la résolution de la shadow map
        this.directionalLight.shadow.mapSize.width = resolution;
        this.directionalLight.shadow.mapSize.height = resolution;
        
        // Force la régénération de la shadow map
        this.directionalLight.shadow.map?.dispose();
        this.directionalLight.shadow.map = null;
        
        // Avertissement pour les hautes résolutions
        let warning = '';
        if (quality === 'ultra') {
            warning = ' ⚠️ ATTENTION: Consommation mémoire élevée (~1GB VRAM)';
        }
        
        console.log(`🌫️ Qualité ombres mise à jour: ${quality} (${resolution}x${resolution})${warning}`);
    }

    /**
     * Met à jour la douceur des ombres (version simplifiée - PCF fixe)
     */
    updateShadowSoftness(softness) {
        if (!this.directionalLight || !this.directionalLight.shadow) {
            return;
        }

        // Stocke la valeur de douceur dans les settings
        this.settings.shadowSoftness = softness;

        // Utilise toujours PCF Soft pour les ombres douces
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        
        console.log(`🌫️ Douceur ombres: ${softness} (PCF Soft fixe)`);
        
        // Ajuste l'intensité des ombres avec la valeur fixe 3.0
        const ambientLights = this.scene.children.filter(child => child.type === 'AmbientLight');
        if (ambientLights.length > 0) {
            // Intensité ambiante réduite pour ombres très douces (3.0)
            ambientLights[0].intensity = 0.4; // Valeur fixe pour softness=3.0
        }
        
        // Force la re-application des paramètres d'ombres
        if (this.directionalLight && this.settings.sunPosition !== undefined) {
            this.updateSunPosition(this.settings.sunPosition);
        }
    }

    /**
     * Obtient le nom lisible du type de shadow map actuel
     */
    getShadowMapTypeName() {
        switch (this.renderer.shadowMap.type) {
            case THREE.BasicShadowMap: return 'Basic';
            case THREE.PCFShadowMap: return 'PCF';
            case THREE.PCFSoftShadowMap: return 'PCF Soft';
            case THREE.VSMShadowMap: return 'VSM';
            default: return 'Unknown';
        }
    }

    /**
     * Gestion du redimensionnement
     */
    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }



    /**
     * Boucle d'animation
     */
    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        
        // Met à jour le compteur de frames pour le dithering temporel
        this.updateFrameCount();
        
        // Met à jour les contrôles
        if (this.controls) {
            this.controls.update();
        }
        
        // Met à jour l'animation de pulsation du soleil
        this.updateSunPulsing();
        
        // Force le rendu
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    /**
     * Génère un pattern de dithering temporel stable
     */
    generateDitherPattern() {
        const patternSize = 16;
        const pattern = [];
        
        for (let i = 0; i < patternSize; i++) {
            // Pattern en spirale de Halton pour distribution uniforme
            const angle = i * 2.399963229728653; // Angle d'or
            const radius = Math.sqrt(i / patternSize) * 0.02; // Rayon progressif
            pattern.push({
                x: Math.cos(angle) * radius,
                z: Math.sin(angle) * radius
            });
        }
        
        return pattern;
    }
    
    /**
     * Obtient l'offset de dithering temporel stable
     */
    getTemporalDither() {
        const patternIndex = this.frameCount % this.ditherPattern.length;
        this.frameCount++;
        
        // Ajoute une légère variation temporelle pour éviter les motifs fixes
        const timeVariation = Math.sin(this.frameCount * 0.01) * 0.005;
        
        return {
            x: this.ditherPattern[patternIndex].x + timeVariation,
            z: this.ditherPattern[patternIndex].z + timeVariation
        };
    }
    
    /**
     * Calcule le bias adaptatif intelligent basé sur l'angle et la distance
     */
    calculateSmartBias(angle, height, angleFactor, heightNormalized, isEdgeCase, isCriticalAngle, isExtremeAngle) {
        // Facteur de distance : plus le soleil est loin, plus on a besoin de bias
        const distanceFactor = Math.max(0.1, Math.min(1.0, height / 100));
        
        // Facteur d'angle : les angles rasants nécessitent plus de correction
        const angleStress = Math.pow(angleFactor, 1.5); // Courbe non-linéaire
        
        // Facteur de terrain : adapté à la complexité du terrain
        const terrainComplexity = this.getTerrainComplexityFactor();
        
        let baseBias, normalBias, radius;
        
        if (isEdgeCase) {
            // Cas très extrêmes avec correction intelligente
            baseBias = -0.0002 * (1 + angleStress) * terrainComplexity - 0.0001 * (1 - distanceFactor);
            normalBias = 0.02 + (0.015 * angleStress) + (0.01 * terrainComplexity);
            radius = 8 + (4 * angleStress) + (2 * terrainComplexity);
            console.log(`🚨 Bias adaptatif CRITIQUE activé: angle=${angle.toFixed(0)}°, bias=${baseBias.toFixed(5)}`);
        } else if (isCriticalAngle) {
            // Angles critiques avec adaptation progressive
            baseBias = -0.00015 * (1 + angleStress * 0.8) * terrainComplexity - 0.00008 * (1 - distanceFactor);
            normalBias = 0.015 + (0.012 * angleStress) + (0.008 * terrainComplexity);
            radius = 6 + (3 * angleStress) + (1.5 * terrainComplexity);
        } else if (isExtremeAngle) {
            // Angles extrêmes avec correction modérée
            baseBias = -0.0001 * (1 + angleStress * 0.6) * terrainComplexity - 0.00005 * (1 - distanceFactor);
            normalBias = 0.012 + (0.01 * angleStress) + (0.006 * terrainComplexity);
            radius = 5 + (2 * angleStress) + (1 * terrainComplexity);
        } else {
            // Angles normaux avec paramètres optimaux
            baseBias = -0.00008 * terrainComplexity - 0.00003 * (1 - heightNormalized);
            normalBias = 0.01 + (0.005 * terrainComplexity) + (0.003 * (1 - heightNormalized));
            radius = 4 + (2 * terrainComplexity) + (1 * (1 - heightNormalized));
        }
        
        // Assure des valeurs dans des plages raisonnables
        baseBias = Math.max(-0.001, Math.min(0, baseBias));
        normalBias = Math.max(0.005, Math.min(0.05, normalBias));
        radius = Math.max(2, Math.min(12, radius));
        
        return { bias: baseBias, normalBias, radius };
    }
    
    /**
     * Estime la complexité du terrain pour adapter les paramètres d'ombres
     */
    getTerrainComplexityFactor() {
        if (!this.currentTerrainData || !this.currentTerrainData.stats) {
            return 1.0; // Valeur par défaut
        }
        
        const stats = this.currentTerrainData.stats;
        
        // Combine plusieurs métriques pour estimer la complexité
        const roughnessFactor = Math.min(2.0, stats.roughness * 5); // Rugosité du terrain
        const elevationRange = stats.max - stats.min; // Étendue d'élévation
        const variabilityFactor = Math.min(2.0, stats.stdDev * 3); // Variabilité
        
        // Facteur de complexité combiné (entre 0.5 et 2.5)
        const complexity = 0.5 + (roughnessFactor + elevationRange + variabilityFactor) / 3;
        
        return Math.max(0.5, Math.min(2.5, complexity));
    }
    
    /**
     * Met à jour le compteur de frames pour le dithering temporel
     */
    updateFrameCount() {
        this.frameCount = (this.frameCount + 1) % 10000; // Évite l'overflow
    }
    
    /**
     * Génère une depth map basée sur la vue actuelle de la caméra
     * @param {number} width - Largeur de la depth map (défaut: 512)
     * @param {number} height - Hauteur de la depth map (défaut: 512)
     * @returns {Object} - Objet contenant la depth map et les métadonnées
     */
    generateDepthMap(width = 512, height = 512) {
        if (!this.renderer || !this.scene || !this.camera) {
            console.error('❌ Impossible de générer la depth map: renderer, scene ou camera non initialisés');
            return null;
        }

        console.log(`📊 Génération de depth map ${width}x${height}...`);

        // Sauvegarde les paramètres actuels du renderer
        const originalSize = this.renderer.getSize(new THREE.Vector2());
        const originalPixelRatio = this.renderer.getPixelRatio();

        try {
            // Configure le renderer pour la capture
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(1); // Évite l'upscaling

            // Crée un render target avec texture de profondeur
            const renderTarget = new THREE.WebGLRenderTarget(width, height, {
                minFilter: THREE.NearestFilter,
                magFilter: THREE.NearestFilter,
                format: THREE.RGBAFormat,
                type: THREE.FloatType,
                depthTexture: new THREE.DepthTexture()
            });

            // Active le rendu de la depth map
            this.renderer.setRenderTarget(renderTarget);
            
            // Rendu de la scène avec les matériaux originaux
            this.renderer.render(this.scene, this.camera);

            // Crée un shader de post-processing pour lire la texture de profondeur
            const postProcessShader = {
                vertexShader: `
                    varying vec2 vUv;
                    void main() {
                        vUv = uv;
                        gl_Position = vec4(position, 1.0);
                    }
                `,
                fragmentShader: `
                    uniform sampler2D depthTexture;
                    uniform float near;
                    uniform float far;
                    varying vec2 vUv;
                    
                    void main() {
                        // Inverse les coordonnées Y pour corriger l'orientation
                        vec2 correctedUv = vec2(vUv.x, 1.0 - vUv.y);
                        
                        // Lit la valeur de profondeur depuis la texture
                        float depth = texture2D(depthTexture, correctedUv).r;
                        
                        // Convertit la profondeur normalisée en distance linéaire
                        float linearDepth = (2.0 * near * far) / (far + near - depth * (far - near));
                        
                        // Normalise entre 0 et 1
                        float normalizedDepth = (linearDepth - near) / (far - near);
                        normalizedDepth = clamp(normalizedDepth, 0.0, 1.0);
                        
                        // Applique une transformation pour améliorer le contraste
                        float enhancedDepth = pow(normalizedDepth, 0.3);
                        
                        // Inverse pour que les objets proches soient blancs
                        float invertedDepth = 1.0 - enhancedDepth;
                        
                        gl_FragColor = vec4(invertedDepth, invertedDepth, invertedDepth, 1.0);
                    }
                `
            };

            // Crée un matériau de post-processing
            const postProcessMaterial = new THREE.ShaderMaterial({
                vertexShader: postProcessShader.vertexShader,
                fragmentShader: postProcessShader.fragmentShader,
                uniforms: {
                    depthTexture: { value: renderTarget.depthTexture },
                    near: { value: this.camera.near },
                    far: { value: this.camera.far }
                }
            });

            // Crée un plan pour le post-processing
            const postProcessPlane = new THREE.PlaneGeometry(2, 2);
            const postProcessMesh = new THREE.Mesh(postProcessPlane, postProcessMaterial);

            // Crée un render target pour le résultat final
            const finalRenderTarget = new THREE.WebGLRenderTarget(width, height, {
                minFilter: THREE.NearestFilter,
                magFilter: THREE.NearestFilter,
                format: THREE.RGBAFormat,
                type: THREE.FloatType
            });

            // Rendu du post-processing
            this.renderer.setRenderTarget(finalRenderTarget);
            this.renderer.render(postProcessMesh, new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1));

            // Récupère les données de profondeur
            const depthData = new Float32Array(width * height * 4);
            this.renderer.readRenderTargetPixels(finalRenderTarget, 0, 0, width, height, depthData);

            // Convertit les données de profondeur en image
            const depthImage = this.convertDepthToImage(depthData, width, height);

            // Récupère les métadonnées de la caméra
            const cameraInfo = {
                position: this.camera.position.clone(),
                rotation: this.camera.rotation.clone(),
                fov: this.camera.fov,
                aspect: this.camera.aspect,
                near: this.camera.near,
                far: this.camera.far
            };

            // Restaure les paramètres originaux
            this.renderer.setRenderTarget(null);
            this.renderer.setSize(originalSize.x, originalSize.y);
            this.renderer.setPixelRatio(originalPixelRatio);

            // Nettoie les ressources
            renderTarget.dispose();
            finalRenderTarget.dispose();
            postProcessMaterial.dispose();
            postProcessPlane.dispose();

            console.log(`✅ Depth map générée: ${width}x${height}`);
            
            return {
                depthData: depthData,
                depthImage: depthImage,
                width: width,
                height: height,
                cameraInfo: cameraInfo,
                timestamp: Date.now()
            };

        } catch (error) {
            console.error('❌ Erreur lors de la génération de la depth map:', error);
            
            // Restaure les paramètres en cas d'erreur
            this.renderer.setRenderTarget(null);
            this.renderer.setSize(originalSize.x, originalSize.y);
            this.renderer.setPixelRatio(originalPixelRatio);
            
            return null;
        }
    }

    /**
     * Convertit les données de profondeur en image visible
     * @param {Float32Array} depthData - Données de profondeur RGBA
     * @param {number} width - Largeur
     * @param {number} height - Hauteur
     * @returns {ImageData} - Image convertie
     */
    convertDepthToImage(depthData, width, height) {
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        const imageData = ctx.createImageData(width, height);
        const data = imageData.data;

        // Les données sont déjà traitées par le shader (0-1)
        // Le shader inverse déjà la profondeur (blanc = proche, noir = lointain)
        
        for (let i = 0; i < depthData.length; i += 4) {
            const pixelIndex = i;
            const depth = depthData[i]; // Canal R (déjà traité par le shader)
            
            if (depth >= 0 && depth <= 1) {
                // Convertit directement en niveaux de gris
                const intensity = Math.floor(depth * 255);
                
                data[pixelIndex] = intensity;     // R
                data[pixelIndex + 1] = intensity; // G
                data[pixelIndex + 2] = intensity; // B
                data[pixelIndex + 3] = 255;       // A
            } else {
                // Pixels sans profondeur (fond) en noir
                data[pixelIndex] = 0;     // R
                data[pixelIndex + 1] = 0; // G
                data[pixelIndex + 2] = 0; // B
                data[pixelIndex + 3] = 255; // A
            }
        }

        return imageData;
    }

    /**
     * Arrête l'animation
     */
    dispose() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        // Nettoie le soleil 3D
        if (this.sunMesh) {
            this.scene.remove(this.sunMesh);
            this.sunMesh.geometry.dispose();
            this.sunMesh.material.dispose();
            this.sunMesh = null;
        }
        this.sunAnimationReady = false;
        
        if (this.renderer) {
            this.renderer.dispose();
        }
    }
} 