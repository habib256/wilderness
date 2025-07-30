/**
 * Point d'entrée principal de l'application Wilderness Terrain Viewer 3D
 */

// Variables globales
let terrainLoader;
let terrainRenderer;
let uiController;

// Configuration de l'application
const CONFIG = {
    defaultTerrain: 'heightmap',
    debugMode: true
};

/**
 * Initialisation de l'application
 */
async function initializeApp() {
    try {
        console.log('🚀 Initialisation Wilderness Terrain Viewer 3D...');
        
        // Vérification WebGL
        if (!checkWebGLSupport()) {
            throw new Error('WebGL non supporté par ce navigateur');
        }
        
        console.log('📦 Initialisation des composants...');
        
        // Initialise le loader de terrain
        terrainLoader = new TerrainLoader();
        
        // Initialise le renderer 3D 
        terrainRenderer = new TerrainRenderer();
        
        // Initialise le contrôleur UI
        uiController = new UIController(terrainLoader, terrainRenderer);
        
        console.log('✅ Tous les composants initialisés');
        
        // Masque l'écran de chargement
        hideLoadingScreen();
        
        // Charge le terrain initial
        console.log('🚀 Chargement du terrain initial...');
        await uiController.switchTerrain(CONFIG.defaultTerrain);
        
        // Précharge les autres terrains en arrière-plan
        console.log('📦 Préchargement des terrains en arrière-plan...');
        preloadTerrains();
        
        console.log('✅ Application initialisée avec succès');
        
    } catch (error) {
        console.error('❌ Erreur lors de l\'initialisation:', error);
        showError('Erreur d\'initialisation: ' + error.message);
    }
}

/**
 * Vérifie le support WebGL
 */
function checkWebGLSupport() {
    try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        return !!gl;
    } catch (e) {
        return false;
    }
}

/**
 * Masque l'écran de chargement
 */
function hideLoadingScreen() {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.classList.add('hidden');
        setTimeout(() => {
            loading.style.display = 'none';
        }, 500);
    }
}

/**
 * Affiche une erreur
 */
function showError(message) {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.innerHTML = `
            <div style="color: #ff6b6b; text-align: center;">
                <h2>❌ Erreur</h2>
                <p>${message}</p>
                <button onclick="location.reload()" style="margin-top: 20px; padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    Recharger la page
                </button>
            </div>
        `;
    }
}

/**
 * Précharge les terrains en arrière-plan
 */
async function preloadTerrains() {
    const terrains = ['montagneux', 'vallonne', 'archipel'];
    
    for (const terrain of terrains) {
        try {
            await terrainLoader.loadTerrain(terrain);
            console.log(`✅ Terrain ${terrain} préchargé`);
        } catch (error) {
            console.warn(`⚠️ Échec préchargement ${terrain}:`, error);
        }
    }
    
    console.log('✅ Préchargement terminé');
}

/**
 * Gestion des erreurs globales
 */
window.addEventListener('error', (event) => {
    console.error('❌ Erreur globale:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('❌ Promise rejetée:', event.reason);
});

/**
 * Démarrage de l'application quand le DOM est prêt
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM chargé');
    
    // Informations système pour debug
    console.log('🖥️ Informations système:');
    console.log(`   Navigateur: ${navigator.userAgent}`);
    console.log(`   Taille écran: ${window.innerWidth}x${window.innerHeight}`);
    console.log(`   Pixel ratio: ${window.devicePixelRatio}`);
    console.log(`   Mémoire: ${navigator.deviceMemory || 'N/A'}GB`);
    console.log(`   Cores CPU: ${navigator.hardwareConcurrency || 'N/A'}`);
    
    // Force l'affichage du canvas
    const canvas = document.getElementById('canvas3d');
    if (canvas) {
        canvas.style.display = 'block';
        canvas.style.visibility = 'visible';
        console.log('🎯 Canvas forcé visible');
    }
    
    // Initialise l'application
    initializeApp();
});

/**
 * Détection des performances
 */
function detectPerformance() {
    const gl = document.createElement('canvas').getContext('webgl');
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    
    if (debugInfo) {
        const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        
        console.log('🔧 GPU Info:', { vendor, renderer });
        
        // Ajuste automatiquement la résolution pour les GPU faibles
        if (renderer.toLowerCase().includes('intel') || 
            renderer.toLowerCase().includes('integrated')) {
            console.log('⚡ GPU intégré détecté, réduction de la résolution par défaut');
            
            // Réduit la résolution par défaut
            setTimeout(() => {
                const resolutionSlider = document.getElementById('resolution');
                if (resolutionSlider) {
                    resolutionSlider.value = 128;
                    resolutionSlider.dispatchEvent(new Event('input'));
                }
            }, 1000);
        }
    }
}

/**
 * Informations de débogage
 */
function logSystemInfo() {
    console.log('🖥️  Informations système:');
    console.log('   Navigateur:', navigator.userAgent);
    console.log('   Taille écran:', `${window.innerWidth}x${window.innerHeight}`);
    console.log('   Pixel ratio:', window.devicePixelRatio);
    console.log('   Mémoire:', navigator.deviceMemory ? `${navigator.deviceMemory}GB` : 'Inconnue');
    console.log('   Cores CPU:', navigator.hardwareConcurrency || 'Inconnu');
}

/**
 * Easter egg - Konami Code
 */
function setupEasterEgg() {
    const konamiCode = [
        'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
        'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
        'KeyB', 'KeyA'
    ];
    let konamiIndex = 0;

    document.addEventListener('keydown', (event) => {
        if (event.code === konamiCode[konamiIndex]) {
            konamiIndex++;
            if (konamiIndex === konamiCode.length) {
                console.log('🎮 Konami Code activé!');
                
                // Active un mode spécial
                if (terrainRenderer) {
                    terrainRenderer.scene.background = new THREE.Color(0x000011);
                    
                    // Ajoute des étoiles
                    const starGeometry = new THREE.BufferGeometry();
                    const starMaterial = new THREE.PointsMaterial({ color: 0xffffff, size: 2 });
                    
                    const starVertices = [];
                    for (let i = 0; i < 1000; i++) {
                        starVertices.push(
                            (Math.random() - 0.5) * 2000,
                            (Math.random() - 0.5) * 2000,
                            (Math.random() - 0.5) * 2000
                        );
                    }
                    
                    starGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starVertices, 3));
                    const stars = new THREE.Points(starGeometry, starMaterial);
                    terrainRenderer.scene.add(stars);
                }
                
                konamiIndex = 0;
            }
        } else {
            konamiIndex = 0;
        }
    });
}

/**
 * Nettoyage à la fermeture
 */
function setupCleanup() {
    window.addEventListener('beforeunload', () => {
        if (terrainRenderer) {
            terrainRenderer.dispose();
        }
        console.log('🧹 Nettoyage terminé');
    });
}

/**
 * Point d'entrée principal
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('📄 DOM chargé');
    
    // Initialise l'application
    initializeApp();
});

// Gestion du focus/blur pour optimiser les performances
document.addEventListener('visibilitychange', () => {
    if (terrainRenderer) {
        if (document.hidden) {
            // Réduit les FPS quand l'onglet n'est pas visible
            console.log('🔇 Onglet caché, réduction FPS');
        } else {
            // Reprend le rendu normal
            console.log('👁️ Onglet visible, reprise FPS normal');
        }
    }
});

/**
 * Informations de version
 */
console.log(`
🏔️ Wilderness Terrain Viewer 3D v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎮 Contrôles:
   • Clic gauche + drag: Rotation caméra
   • Molette: Zoom
   • Clic droit + drag: Pan
   • R: Reset caméra
   • 1-5: Sélection terrain
   • W: Toggle wireframe  
   • C: Cycle modes couleur

🏗️ Architecture:
   • Three.js r128 pour le rendu 3D
   • Canvas API pour traitement heightmaps
   • Web Workers pour calculs (si supporté)
   
🧬 Générateur procédural:
   • Diamond-Square + Perlin fBm
   • Export PNG 16-bit
   • Validation statistique
   
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`); 