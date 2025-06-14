"""Configuration management model."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import pygame as pg

from src.core.constants import (
    CONFIG_FILE, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT, DEFAULT_MUSIC_VOLUME,
    ALLOWED_FPS_VALUES, WINDOW_TITLE
)
from src.core.exceptions import ConfigError


@dataclass
class KeyBindings:
    """Player control key bindings."""
    
    left: int = pg.K_a
    right: int = pg.K_d
    jump: int = pg.K_SPACE
    sprint: int = pg.K_LSHIFT
    block: int = pg.K_f
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> KeyBindings:
        """Create from dictionary format."""
        return cls(**data)


@dataclass
class DisplaySettings:
    """Display-related settings."""
    
    vsync: bool = True
    fps_limit: int = 60
    fullscreen: bool = True  # Default to fullscreen mode, now forced
    window_width: int = DEFAULT_WINDOW_WIDTH
    window_height: int = DEFAULT_WINDOW_HEIGHT
    
    def __post_init__(self):
        """Validate settings after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate display settings."""
        if self.fps_limit not in ALLOWED_FPS_VALUES:
            self.fps_limit = 60
        
        if self.window_width < MIN_WINDOW_WIDTH:
            self.window_width = MIN_WINDOW_WIDTH
        
        if self.window_height < MIN_WINDOW_HEIGHT:
            self.window_height = MIN_WINDOW_HEIGHT
    
    @property
    def window_size(self) -> tuple[int, int]:
        """Get window size as tuple."""
        return (self.window_width, self.window_height)


@dataclass
class AudioSettings:
    """Audio-related settings."""
    
    music_volume: float = DEFAULT_MUSIC_VOLUME
    sound_volume: float = DEFAULT_MUSIC_VOLUME
    
    def __post_init__(self):
        """Validate settings after initialization."""
        self.music_volume = max(0.0, min(1.0, self.music_volume))
        self.sound_volume = max(0.0, min(1.0, self.sound_volume))


class Config:
    """Game configuration manager following single responsibility principle."""
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize configuration."""
        self._config_path = Path(config_path or CONFIG_FILE)
        self._key_bindings: KeyBindings = KeyBindings()
        self._display: DisplaySettings = DisplaySettings()
        self._audio: AudioSettings = AudioSettings()
        self._screen: Optional[pg.Surface] = None
        self._load()
    
    # Properties for encapsulation
    @property
    def key_bindings(self) -> KeyBindings:
        """Get key bindings (read-only)."""
        return self._key_bindings
    
    @property
    def display(self) -> DisplaySettings:
        """Get display settings (read-only)."""
        return self._display
    
    @property
    def audio(self) -> AudioSettings:
        """Get audio settings (read-only)."""
        return self._audio
    
    @property
    def screen(self) -> Optional[pg.Surface]:
        """Get current screen surface."""
        return self._screen
    
    # Public methods
    def update_key_binding(self, action: str, key: int) -> None:
        """Update a key binding, ensuring no duplicates."""
        if not hasattr(self._key_bindings, action):
            raise ConfigError(f"Invalid action: {action}")
        
        # Remove duplicate bindings
        for attr_name in vars(self._key_bindings):
            if getattr(self._key_bindings, attr_name) == key:
                setattr(self._key_bindings, attr_name, 0)
        
        setattr(self._key_bindings, action, key)
    
    def toggle_vsync(self) -> None:
        """Toggle vsync setting."""
        self._display.vsync = not self._display.vsync
        self._recreate_display()
    
    def cycle_fps_limit(self) -> None:
        """Cycle through available FPS limits."""
        if self._display.vsync:
            return
        
        current_index = ALLOWED_FPS_VALUES.index(self._display.fps_limit)
        next_index = (current_index + 1) % len(ALLOWED_FPS_VALUES)
        self._display.fps_limit = ALLOWED_FPS_VALUES[next_index]
    
    def set_music_volume(self, volume: float) -> None:
        """Set music volume."""
        self._audio.music_volume = max(0.0, min(1.0, volume))
        if pg.mixer.get_init():
            pg.mixer.music.set_volume(self._audio.music_volume)
    
    def set_sound_volume(self, volume: float) -> None:
        """Set sound effects volume."""
        self._audio.sound_volume = max(0.0, min(1.0, volume))
    
    def create_display(self) -> pg.Surface:
        """Create or recreate the display surface."""
        flags = pg.DOUBLEBUF | pg.RESIZABLE
        
        if self._display.fullscreen:
            flags |= pg.FULLSCREEN
            size = (0, 0)  # Let SDL choose current resolution
        else:
            size = self._display.window_size
            flags |= pg.SCALED
        
        vsync = 1 if self._display.vsync else 0
        
        try:
            self._screen = pg.display.set_mode(size, flags, vsync=vsync)
            pg.display.set_caption(WINDOW_TITLE)
        except pg.error as e:
            # Fallback to windowed mode with minimum size
            self._display.fullscreen = False
            self._display.window_width = MIN_WINDOW_WIDTH
            self._display.window_height = MIN_WINDOW_HEIGHT
            
            self._screen = pg.display.set_mode(
                (MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT),
                pg.RESIZABLE
            )
            pg.display.set_caption(WINDOW_TITLE)
            
            raise ConfigError(f"Failed to create display: {e}")
        
        return self._screen
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            data = self._to_dict()
            self._config_path.write_text(
                json.dumps(data, indent=2),
                encoding='utf-8'
            )
        except (IOError, json.JSONEncodeError) as e:
            raise ConfigError(f"Failed to save configuration: {e}")
    
    # Private methods
    def _load(self) -> None:
        """Load configuration from file."""
        if not self._config_path.exists():
            return
        
        try:
            data = json.loads(self._config_path.read_text(encoding='utf-8'))
            self._from_dict(data)
        except (IOError, json.JSONDecodeError) as e:
            # Log error but continue with defaults
            print(f"Failed to load configuration: {e}")
    
    def _recreate_display(self) -> None:
        """Recreate the display surface."""
        if self._screen is not None:
            self.create_display()
    
    def _to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'key_bindings': self._key_bindings.to_dict(),
            'display': asdict(self._display),
            'audio': asdict(self._audio),
        }
    
    def _from_dict(self, data: Dict[str, Any]) -> None:
        """Load configuration from dictionary."""
        if 'key_bindings' in data:
            self._key_bindings = KeyBindings.from_dict(data.get('key_bindings', {}))
        
        if 'display' in data:
            display_data = data.get('display', {})
            self._display = DisplaySettings(**display_data)
        
        if 'audio' in data:
            audio_data = data.get('audio', {})
            self._audio = AudioSettings(**audio_data)
        
        # Validate loaded display settings
        self._display._validate()