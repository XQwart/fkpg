"""Base scene controller with common functionality."""
from __future__ import annotations

from abc import ABC
from typing import Optional
import pygame as pg

from src.core.interfaces import IScene
from src.models.config import Config


class BaseScene(IScene):
    """Base class for all game scenes with common functionality."""
    
    def __init__(self, config: Config) -> None:
        """Initialize base scene."""
        self._config = config
        self._clock = pg.time.Clock()
        self._running = True
        self._next_scene: Optional[str] = None
        self._delta_time = 0.0
        self._fps_limit = 0
        
        # Update FPS limit from config
        self._update_fps_limit()
    
    @property
    def config(self) -> Config:
        """Get configuration object."""
        return self._config
    
    @property
    def screen(self) -> pg.Surface:
        """Get current screen surface."""
        return self._config.screen or pg.display.get_surface()
    
    @property
    def delta_time(self) -> float:
        """Get time elapsed since last frame in seconds."""
        return self._delta_time
    
    def run(self) -> Optional[str]:
        """
        Run the scene loop.
        
        Returns:
            Identifier of next scene to transition to, or None to exit
        """
        self.on_enter()
        
        while self._running and self._next_scene is None:
            # Handle events
            action = self.handle_events()
            if action:
                self._next_scene = action
                break
            
            # Update
            self.update(self._delta_time)
            
            # Render
            self.render()
            
            # Update display
            pg.display.flip()
            
            # Tick clock
            self._tick()
        
        self.on_exit()
        return self._next_scene
    
    def transition_to(self, scene_id: str) -> None:
        """Request transition to another scene."""
        self._next_scene = scene_id
        self._running = False
    
    def on_enter(self) -> None:
        """Called when scene becomes active. Override in subclasses."""
        self._running = True
        self._next_scene = None
        self._update_fps_limit()
    
    def on_exit(self) -> None:
        """Called when scene becomes inactive. Override in subclasses."""
        pass
    
    def _tick(self) -> None:
        """Update clock and calculate delta time."""
        # Use vsync or FPS limit
        if self._config.display.vsync:
            self._delta_time = self._clock.tick(0) / 1000.0
        else:
            self._delta_time = self._clock.tick(self._fps_limit) / 1000.0
    
    def _update_fps_limit(self) -> None:
        """Update FPS limit from config."""
        self._fps_limit = self._config.display.fps_limit
    
    def _handle_common_events(self, event: pg.event.Event) -> Optional[str]:
        """
        Handle common events across all scenes.
        
        Returns:
            Action string if event should trigger scene change
        """
        if event.type == pg.QUIT:
            return "exit"
        
        # Handle alt+enter for fullscreen toggle
        if event.type == pg.KEYDOWN:
            keys = pg.key.get_pressed()
            if event.key == pg.K_RETURN and (keys[pg.K_LALT] or keys[pg.K_RALT]):
                self._config.toggle_fullscreen()
                return None
        
        return None