"""
Module de génération procédurale de terrain.

Contient:
- heightmap.py : Génération Diamond-Square + Perlin fBm  
- erosion.py : Érosion hydraulique GPU
- progress.py : Système de suivi de progression
"""

__version__ = "0.1.0"
__author__ = "Wilderness Team"

# Imports conditionnels pour éviter RuntimeWarning avec python -m
import sys
import warnings

# Supprime le RuntimeWarning spécifique aux modules exécutés avec -m
warnings.filterwarnings("ignore", 
                       message=".*found in sys.modules after import.*", 
                       category=RuntimeWarning)

from .heightmap import HeightMapGenerator, DiamondSquare, PerlinFBm
from .erosion import HydraulicErosion, ErosionPipeline, erode_heightmap
from .real_terrain_extractor import (
    ReunionTerrainExtractor, OpenTopographyAPI, OpenElevationAPI,
    TerrainBounds, ReunionTerrainBounds
)
from .progress import (
    ProgressTracker, ConsoleProgressCallback, WebSocketProgressCallback,
    ProgressStage, ProgressInfo, ProgressCallback,
    get_progress_tracker, set_progress_tracker
)

__all__ = [
    "HeightMapGenerator", 
    "DiamondSquare", 
    "PerlinFBm",
    "HydraulicErosion",
    "ErosionPipeline", 
    "erode_heightmap",
    "ReunionTerrainExtractor",
    "OpenTopographyAPI",
    "OpenElevationAPI",
    "TerrainBounds",
    "ReunionTerrainBounds",
    "ProgressTracker",
    "ConsoleProgressCallback",
    "WebSocketProgressCallback", 
    "ProgressStage",
    "ProgressInfo",
    "ProgressCallback",
    "get_progress_tracker",
    "set_progress_tracker"
] 