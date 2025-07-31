/**
 * TerrainLoader - Charge et traite les heightmaps PNG
 */
class TerrainLoader {
    constructor() {
        this.terrains = new Map();
        this.currentTerrain = null;
        this.loadingPromises = new Map();
    }

    /**
     * Vide le cache des terrains pour forcer leur rechargement
     */
    clearCache() {
        console.log('🗑️ Vidage du cache des terrains');
        this.terrains.clear();
        this.loadingPromises.clear();
    }

    /**
     * Configuration des terrains disponibles
     */
    getTerrainConfig() {
        return {
            'montagneux': {
                name: 'Montagneux',
                emoji: '⛰️',
                path: 'images/montagneux.png',
                description: 'Terrain rugueux avec beaucoup de détails (ds_roughness=0.8, octaves=8)',
                expectedSize: 2048
            },
            'vallonne': {
                name: 'Vallonné', 
                emoji: '🌊',
                path: 'images/vallonne.png',
                description: 'Terrain doux avec ondulations (ds_roughness=0.4, octaves=4)',
                expectedSize: 2048
            },
            'archipel': {
                name: 'Archipel',
                emoji: '🏝️',
                path: 'images/archipel.png', 
                description: 'Îles créées par seuillage (threshold=0.4)',
                expectedSize: 2048
            },
            'heightmap': {
                name: 'Standard',
                emoji: '🗻',
                path: 'images/heightmap.png',
                description: 'Terrain avec paramètres par défaut',
                expectedSize: 2048
            },
            'reunion': {
                name: 'Réunion',
                emoji: '🏝️',
                path: 'images/reunion_real_native.png',
                description: 'Île de la Réunion - Données d\'élévation réelles (1000×1000, ~58m/pixel)',
                expectedSize: 1000,
                isRealTerrain: true,
                coordinates: {
                    center: [-21.13, 55.53],
                    bounds: [[-20.871, 55.214], [-21.389, 55.838]],
                    dimensions: "58 × 69 km",
                    precision: "~58m par pixel",
                    source: "OpenElevation API",
                    quality: "Données natives 1000×1000"
                }
            },
            'honshu_kanto': {
                name: 'Honshu Kanto',
                emoji: '🗾',
                path: 'images/honshu_kanto_hd.png',
                description: 'Région Kanto (Japon) - Tokyo, mont Fuji (1500×1500, ~111m/pixel)',
                expectedSize: 1500,
                isRealTerrain: true,
                coordinates: {
                    center: [35.75, 139.50],
                    bounds: [[36.5, 138.5], [35.0, 140.5]],
                    dimensions: "167 × 167 km",
                    precision: "~111m par pixel",
                    source: "OpenElevation API + NASA SRTM",
                    quality: "Données natives 1500×1500",
                    landmarks: "Mont Fuji (3,776m), Tokyo, Yokohama"
                }
            },
            'eroded': {
                name: 'Érodé',
                emoji: '🏔️',
                path: 'images/eroded_medium.png',
                description: 'Terrain standard avec érosion hydraulique (50 itérations)',
                expectedSize: 1024,
                isEroded: true,
                erosionType: 'standard'
            },
            'yakushima': {
                name: 'Yakushima',
                emoji: '🌿',
                path: 'images/yakushima_full_4k.png',
                description: 'Île de Yakushima (Japon) - Site UNESCO, Mont Miyanoura 1 936m',
                expectedSize: 1024,
                isEroded: false,
                erosionType: 'none',
                features: {
                    type: 'Île granitique',
                    elevation: '0-1 936m',
                    gradient: 'Mer → 1 936m en 13km',
                    heritage: 'Patrimoine UNESCO 1993',
                    landmarks: 'Mont Miyanoura, Forêt Jōmon-sugi, Cascade Senpiro'
                }
            }
        };
    }

    /**
     * Charge un terrain par son nom
     */
    async loadTerrain(terrainName) {
        // Évite les chargements multiples
        if (this.loadingPromises.has(terrainName)) {
            return this.loadingPromises.get(terrainName);
        }

        // Déjà chargé
        if (this.terrains.has(terrainName)) {
            return this.terrains.get(terrainName);
        }

        const config = this.getTerrainConfig()[terrainName];
        if (!config) {
            throw new Error(`Terrain inconnu: ${terrainName}`);
        }

        // Crée la promesse de chargement
        const loadPromise = this._loadTerrainData(terrainName, config);
        this.loadingPromises.set(terrainName, loadPromise);

        try {
            const terrainData = await loadPromise;
            this.terrains.set(terrainName, terrainData);
            this.loadingPromises.delete(terrainName);
            return terrainData;
        } catch (error) {
            this.loadingPromises.delete(terrainName);
            throw error;
        }
    }

    /**
     * Charge les données d'un terrain depuis l'image PNG (parsing 16-bit)
     */
    async _loadTerrainData(terrainName, config) {
        console.log(`🏔️ Chargement terrain: ${config.name}`);
        
        // Avertissement pour les gros fichiers
        if (config.expectedSize >= 4096) {
            console.warn(`📦 Chargement fichier 16K (${config.expectedSize}²) - Patientez...`);
        }

        try {
            // Fetch le PNG comme ArrayBuffer avec progress tracking
            const response = await fetch(config.path);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const contentLength = response.headers.get('content-length');
            if (contentLength) {
                const totalSize = parseInt(contentLength);
                console.log(`📊 Taille fichier: ${(totalSize / 1024 / 1024).toFixed(1)}MB`);
            }
            
            const arrayBuffer = await response.arrayBuffer();
            const buffer = new Uint8Array(arrayBuffer);
            
            // Parsing PNG basique pour extraire width, height et data
            const { width, height, data } = this.parsePNG16bit(buffer);
            
            // Convertit en Float32 normalisé
            const heightData = new Float32Array(width * height);
            for (let i = 0; i < heightData.length; i++) {
                heightData[i] = data[i] / 65535.0;
            }
            
            // Calcule stats
            const stats = this._calculateStats(heightData, width, height);
            
            const terrainData = {
                name: terrainName,
                config: config,
                width: width,
                height: height,
                heightData: heightData,
                stats: stats
            };
            
            console.log(`✅ Terrain ${config.name} chargé: ${width}x${height}, stats:`, stats);
            return terrainData;
            
        } catch (error) {
            console.error(`❌ Erreur chargement PNG ${config.name}:`, error);
            throw error;
        }
    }

    /**
     * Parse un PNG 16-bit grayscale en JS
     */
    parsePNG16bit(buffer) {
        let pos = 8; // Skip signature
        
        // Read IHDR
        const ihdrSize = this.readUint32(buffer, pos);
        pos += 4;
        const ihdrType = String.fromCharCode(...buffer.slice(pos, pos+4));
        pos += 4;
        
        if (ihdrType !== 'IHDR') {
            throw new Error('IHDR chunk manquant');
        }
        
        const width = this.readUint32(buffer, pos);
        pos += 4;
        const height = this.readUint32(buffer, pos);
        pos += 4;
        
        const bitDepth = buffer[pos];
        const colorType = buffer[pos + 1];
        pos += 5; // Skip compression, filter, interlace
        
        if (bitDepth !== 16 || colorType !== 0) {
            throw new Error(`Format non supporté: bitDepth=${bitDepth}, colorType=${colorType}`);
        }
        
        // Skip CRC
        pos += 4;
        
        // Trouve IDAT chunks
        const dataChunks = [];
        while (pos < buffer.length) {
            const chunkSize = this.readUint32(buffer, pos);
            pos += 4;
            const chunkType = String.fromCharCode(...buffer.slice(pos, pos+4));
            pos += 4;
            
            if (chunkType === 'IDAT') {
                dataChunks.push(buffer.slice(pos, pos + chunkSize));
            }
            
            pos += chunkSize + 4; // Skip data + CRC
            
            if (chunkType === 'IEND') break;
        }
        
        // Concatène et décompresse IDAT
        const compressedData = this.concatBuffers(dataChunks);
        const inflated = pako.inflate(compressedData);
        
        // Parse les scanlines (grayscale 16-bit: 2 bytes par pixel + 1 byte filter par ligne)
        const bytesPerPixel = 2;
        const bytesPerLine = 1 + (width * bytesPerPixel); // Filter byte + data
        const data = new Uint16Array(width * height);
        let dataIndex = 0;
        
        let prevLine = new Uint8Array(bytesPerLine - 1);
        let currentLine = new Uint8Array(bytesPerLine - 1);
        
        for (let y = 0; y < height; y++) {
            const lineStart = y * bytesPerLine;
            const filter = inflated[lineStart];
            
            // Copie la ligne
            for (let x = 0; x < bytesPerLine - 1; x++) {
                currentLine[x] = inflated[lineStart + 1 + x];
            }
            
            // Applique le filter (seulement Paeth pour simplifier, ou implémenter tous)
            this.unfilterLine(filter, currentLine, prevLine, bytesPerPixel);
            
            // Convertit en Uint16
            for (let x = 0; x < width; x++) {
                const byteIndex = x * bytesPerPixel;
                data[dataIndex++] = (currentLine[byteIndex] << 8) | currentLine[byteIndex + 1];
            }
            
            // Swap lines
            [prevLine, currentLine] = [currentLine, prevLine];
        }
        
        return { width, height, data };
    }

    /**
     * Unfilter une ligne PNG
     */
    unfilterLine(filter, current, previous, bpp) {
        switch (filter) {
            case 0: // None
                break;
            case 1: // Sub
                for (let i = bpp; i < current.length; i++) {
                    current[i] = (current[i] + current[i - bpp]) & 0xff;
                }
                break;
            case 2: // Up
                for (let i = 0; i < current.length; i++) {
                    current[i] = (current[i] + previous[i]) & 0xff;
                }
                break;
            case 3: // Average
                for (let i = 0; i < current.length; i++) {
                    const left = i >= bpp ? current[i - bpp] : 0;
                    const up = previous[i];
                    current[i] = (current[i] + Math.floor((left + up) / 2)) & 0xff;
                }
                break;
            case 4: // Paeth
                for (let i = 0; i < current.length; i++) {
                    const left = i >= bpp ? current[i - bpp] : 0;
                    const up = previous[i];
                    const upLeft = i >= bpp ? previous[i - bpp] : 0;
                    
                    const p = left + up - upLeft;
                    const pa = Math.abs(p - left);
                    const pb = Math.abs(p - up);
                    const pc = Math.abs(p - upLeft);
                    
                    let nearest;
                    if (pa <= pb && pa <= pc) nearest = left;
                    else if (pb <= pc) nearest = up;
                    else nearest = upLeft;
                    
                    current[i] = (current[i] + nearest) & 0xff;
                }
                break;
            default:
                throw new Error(`Filtre PNG non supporté: ${filter}`);
        }
    }

    /**
     * Concatène des buffers
     */
    concatBuffers(buffers) {
        const totalLength = buffers.reduce((acc, buf) => acc + buf.length, 0);
        const result = new Uint8Array(totalLength);
        let offset = 0;
        for (let buf of buffers) {
            result.set(buf, offset);
            offset += buf.length;
        }
        return result;
    }

    /**
     * Lit un uint32 du buffer
     */
    readUint32(buffer, pos) {
        return (buffer[pos] << 24) |
               (buffer[pos+1] << 16) |
               (buffer[pos+2] << 8) |
               buffer[pos+3];
    }

    /**
     * Calcule les statistiques d'un terrain
     */
    _calculateStats(heightData, width, height) {
        let min = Infinity;
        let max = -Infinity;
        let sum = 0;
        let sumSquares = 0;

        // Statistiques de base
        for (let i = 0; i < heightData.length; i++) {
            const h = heightData[i];
            min = Math.min(min, h);
            max = Math.max(max, h);
            sum += h;
            sumSquares += h * h;
        }

        const count = heightData.length;
        const mean = sum / count;
        const variance = (sumSquares / count) - (mean * mean);
        const stdDev = Math.sqrt(variance);

        // Calcul de la rugosité (gradient moyen)
        let gradientSum = 0;
        let gradientCount = 0;

        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const i = y * width + x;
                
                // Gradient en X et Y
                const gx = (heightData[i + 1] - heightData[i - 1]) * 0.5;
                const gy = (heightData[i + width] - heightData[i - width]) * 0.5;
                
                // Magnitude du gradient
                const gradMag = Math.sqrt(gx * gx + gy * gy);
                gradientSum += gradMag;
                gradientCount++;
            }
        }

        const roughness = gradientCount > 0 ? gradientSum / gradientCount : 0;

        return {
            min: min,
            max: max,
            mean: mean,
            stdDev: stdDev,
            roughness: roughness,
            size: `${width}x${height}`,
            pixels: count
        };
    }

    /**
     * Précharge tous les terrains
     */
    async preloadAllTerrains() {
        const terrainNames = Object.keys(this.getTerrainConfig());
        const promises = terrainNames.map(name => this.loadTerrain(name));
        
        try {
            await Promise.all(promises);
            console.log('✅ Tous les terrains préchargés');
        } catch (error) {
            console.warn('⚠️ Erreur préchargement:', error);
        }
    }

    /**
     * Obtient un terrain chargé
     */
    getTerrain(terrainName) {
        return this.terrains.get(terrainName);
    }

    /**
     * Liste tous les terrains disponibles
     */
    getAvailableTerrains() {
        return Object.keys(this.getTerrainConfig());
    }

    /**
     * Définit le terrain actuel
     */
    setCurrentTerrain(terrainName) {
        if (this.terrains.has(terrainName)) {
            this.currentTerrain = terrainName;
            return this.terrains.get(terrainName);
        }
        return null;
    }

    /**
     * Obtient le terrain actuel
     */
    getCurrentTerrain() {
        return this.currentTerrain ? this.terrains.get(this.currentTerrain) : null;
    }
} 