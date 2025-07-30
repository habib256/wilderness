"""
Système de suivi de progression pour la génération de terrain.

Ce module fournit des callbacks flexibles pour suivre l'avancement 
de la génération de heightmaps en temps réel.
"""

import time
import threading
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

class ProgressStage(Enum):
    """Étapes de la génération de terrain."""
    INITIALIZATION = "initialization"
    DIAMOND_SQUARE = "diamond_square"
    PERLIN_FBM = "perlin_fbm"
    BLENDING = "blending"
    NORMALIZATION = "normalization"
    EROSION = "erosion"
    SAVING = "saving"
    COMPLETED = "completed"

@dataclass
class ProgressInfo:
    """Informations de progression."""
    stage: ProgressStage
    stage_progress: float  # 0.0 à 1.0 pour l'étape actuelle
    overall_progress: float  # 0.0 à 1.0 pour l'ensemble du processus
    current_step: str  # Description de l'étape actuelle
    details: Dict[str, Any]  # Informations supplémentaires
    start_time: float
    elapsed_time: float
    estimated_remaining: Optional[float] = None

class ProgressCallback(ABC):
    """Interface abstraite pour les callbacks de progression."""
    
    @abstractmethod
    def on_progress(self, progress: ProgressInfo) -> None:
        """Appelé à chaque mise à jour de progression."""
        pass
    
    @abstractmethod
    def on_stage_start(self, stage: ProgressStage, description: str) -> None:
        """Appelé au début d'une nouvelle étape."""
        pass
    
    @abstractmethod
    def on_stage_complete(self, stage: ProgressStage, duration: float) -> None:
        """Appelé à la fin d'une étape."""
        pass
    
    @abstractmethod
    def on_error(self, stage: ProgressStage, error: Exception) -> None:
        """Appelé en cas d'erreur."""
        pass

class ConsoleProgressCallback(ProgressCallback):
    """Callback de progression pour la console avec barre de progression."""
    
    def __init__(self, show_details: bool = True):
        self.show_details = show_details
        self.last_update = 0
        self.update_interval = 0.1  # Mise à jour max toutes les 100ms
        
    def on_progress(self, progress: ProgressInfo) -> None:
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
            
        self.last_update = current_time
        
        # Barre de progression
        bar_length = 40
        filled_length = int(bar_length * progress.overall_progress)
        bar = '█' * filled_length + '▒' * (bar_length - filled_length)
        
        # Temps estimé restant
        eta_str = ""
        if progress.estimated_remaining:
            eta_str = f" | ETA: {progress.estimated_remaining:.1f}s"
        
        print(f"\r🔄 [{bar}] {progress.overall_progress*100:.1f}% | "
              f"{progress.stage.value} | {progress.current_step}"
              f" | {progress.elapsed_time:.1f}s{eta_str}",
              end='', flush=True)
    
    def on_stage_start(self, stage: ProgressStage, description: str) -> None:
        print(f"\n🎯 {stage.value.title()}: {description}")
    
    def on_stage_complete(self, stage: ProgressStage, duration: float) -> None:
        print(f"\n✅ {stage.value.title()} terminé en {duration:.2f}s")
    
    def on_error(self, stage: ProgressStage, error: Exception) -> None:
        print(f"\n❌ Erreur dans {stage.value}: {error}")

class WebSocketProgressCallback(ProgressCallback):
    """Callback de progression pour WebSocket (interface web)."""
    
    def __init__(self, websocket_sender: Optional[Callable] = None):
        self.websocket_sender = websocket_sender
        self.session_id = None
        
    def set_session_id(self, session_id: str):
        """Définit l'ID de session pour le WebSocket."""
        self.session_id = session_id
    
    def on_progress(self, progress: ProgressInfo) -> None:
        if self.websocket_sender and self.session_id:
            data = {
                'type': 'progress',
                'session_id': self.session_id,
                'stage': progress.stage.value,
                'stage_progress': progress.stage_progress,
                'overall_progress': progress.overall_progress,
                'current_step': progress.current_step,
                'elapsed_time': progress.elapsed_time,
                'estimated_remaining': progress.estimated_remaining,
                'details': progress.details
            }
            self.websocket_sender(data)
    
    def on_stage_start(self, stage: ProgressStage, description: str) -> None:
        if self.websocket_sender and self.session_id:
            data = {
                'type': 'stage_start',
                'session_id': self.session_id,
                'stage': stage.value,
                'description': description
            }
            self.websocket_sender(data)
    
    def on_stage_complete(self, stage: ProgressStage, duration: float) -> None:
        if self.websocket_sender and self.session_id:
            data = {
                'type': 'stage_complete',
                'session_id': self.session_id,
                'stage': stage.value,
                'duration': duration
            }
            self.websocket_sender(data)
    
    def on_error(self, stage: ProgressStage, error: Exception) -> None:
        if self.websocket_sender and self.session_id:
            data = {
                'type': 'error',
                'session_id': self.session_id,
                'stage': stage.value,
                'error': str(error)
            }
            self.websocket_sender(data)

class ProgressTracker:
    """Gestionnaire principal de progression."""
    
    def __init__(self):
        self.callbacks: list[ProgressCallback] = []
        self.start_time = 0
        self.current_stage = ProgressStage.INITIALIZATION
        self.stage_weights = {
            ProgressStage.INITIALIZATION: 0.02,
            ProgressStage.DIAMOND_SQUARE: 0.35,
            ProgressStage.PERLIN_FBM: 0.35,
            ProgressStage.BLENDING: 0.15,
            ProgressStage.NORMALIZATION: 0.08,
            ProgressStage.SAVING: 0.05
        }
        self.stage_progress = 0.0
        self.stage_start_times = {}
        self.stage_durations = {}
        
    def add_callback(self, callback: ProgressCallback):
        """Ajoute un callback de progression."""
        self.callbacks.append(callback)
        
    def remove_callback(self, callback: ProgressCallback):
        """Supprime un callback de progression."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def start(self):
        """Démarre le suivi de progression."""
        self.start_time = time.time()
        self.current_stage = ProgressStage.INITIALIZATION
        self.stage_progress = 0.0
        self.stage_start_times.clear()
        self.stage_durations.clear()
    
    def start_stage(self, stage: ProgressStage, description: str = ""):
        """Démarre une nouvelle étape."""
        # Termine l'étape précédente si nécessaire
        if self.current_stage != stage and self.current_stage in self.stage_start_times:
            self.complete_stage(self.current_stage)
        
        self.current_stage = stage
        self.stage_progress = 0.0
        self.stage_start_times[stage] = time.time()
        
        for callback in self.callbacks:
            try:
                callback.on_stage_start(stage, description)
            except Exception as e:
                print(f"Erreur callback stage_start: {e}")
    
    def update_progress(self, stage_progress: float, current_step: str = "", **details):
        """Met à jour la progression de l'étape actuelle."""
        self.stage_progress = max(0.0, min(1.0, stage_progress))
        
        # Calcul de la progression globale
        overall_progress = 0.0
        for stage, weight in self.stage_weights.items():
            if stage == self.current_stage:
                overall_progress += weight * self.stage_progress
            elif stage in self.stage_durations:
                overall_progress += weight
        
        elapsed_time = time.time() - self.start_time
        
        # Estimation du temps restant
        estimated_remaining = None
        if overall_progress > 0.01:
            total_estimated_time = elapsed_time / overall_progress
            estimated_remaining = total_estimated_time - elapsed_time
        
        progress_info = ProgressInfo(
            stage=self.current_stage,
            stage_progress=self.stage_progress,
            overall_progress=overall_progress,
            current_step=current_step,
            details=details,
            start_time=self.start_time,
            elapsed_time=elapsed_time,
            estimated_remaining=estimated_remaining
        )
        
        for callback in self.callbacks:
            try:
                callback.on_progress(progress_info)
            except Exception as e:
                print(f"Erreur callback progress: {e}")
    
    def complete_stage(self, stage: ProgressStage):
        """Marque une étape comme terminée."""
        if stage in self.stage_start_times:
            duration = time.time() - self.stage_start_times[stage]
            self.stage_durations[stage] = duration
            
            for callback in self.callbacks:
                try:
                    callback.on_stage_complete(stage, duration)
                except Exception as e:
                    print(f"Erreur callback stage_complete: {e}")
    
    def complete(self):
        """Marque la génération comme terminée."""
        if self.current_stage in self.stage_start_times:
            self.complete_stage(self.current_stage)
        
        self.current_stage = ProgressStage.COMPLETED
        self.update_progress(1.0, "Génération terminée")
    
    def error(self, error: Exception):
        """Signale une erreur."""
        for callback in self.callbacks:
            try:
                callback.on_error(self.current_stage, error)
            except Exception as e:
                print(f"Erreur callback error: {e}")

# Instance globale par thread
_thread_local = threading.local()

def get_progress_tracker() -> ProgressTracker:
    """Obtient le tracker de progression pour le thread actuel."""
    if not hasattr(_thread_local, 'progress_tracker'):
        _thread_local.progress_tracker = ProgressTracker()
    return _thread_local.progress_tracker

def set_progress_tracker(tracker: ProgressTracker):
    """Définit le tracker de progression pour le thread actuel."""
    _thread_local.progress_tracker = tracker 