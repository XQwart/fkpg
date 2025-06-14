"""Core interfaces and abstract base classes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, Optional, Any
import pygame as pg


class Renderable(Protocol):
    """Protocol for objects that can be rendered."""
    
    def render(self, surface: pg.Surface) -> None:
        """Render the object to the given surface."""
        ...


class Updatable(Protocol):
    """Protocol for objects that can be updated."""
    
    def update(self, delta_time: float) -> None:
        """Update the object state."""
        ...


class EventHandler(Protocol):
    """Protocol for objects that handle events."""
    
    def handle_event(self, event: pg.event.Event) -> Optional[str]:
        """Handle a pygame event and return an optional action."""
        ...


class IScene(ABC):
    """Abstract base class for all game scenes."""
    
    @abstractmethod
    def handle_events(self) -> Optional[str]:
        """Process input events and return next scene identifier if needed."""
        pass
    
    @abstractmethod
    def update(self, delta_time: float) -> None:
        """Update scene state."""
        pass
    
    @abstractmethod
    def render(self) -> None:
        """Render the scene."""
        pass
    
    @abstractmethod
    def on_enter(self) -> None:
        """Called when scene becomes active."""
        pass
    
    @abstractmethod
    def on_exit(self) -> None:
        """Called when scene becomes inactive."""
        pass


class IEntity(ABC):
    """Abstract base class for game entities."""
    
    @abstractmethod
    def update(self, delta_time: float) -> None:
        """Update entity state."""
        pass
    
    @property
    @abstractmethod
    def position(self) -> pg.math.Vector2:
        """Get entity position."""
        pass
    
    @property
    @abstractmethod
    def rect(self) -> pg.Rect:
        """Get entity bounding rectangle."""
        pass


class IRenderer(ABC):
    """Abstract base class for renderers."""
    
    @abstractmethod
    def render(self, surface: pg.Surface) -> None:
        """Render to the given surface."""
        pass
    
    @abstractmethod
    def update_screen_size(self, width: int, height: int) -> None:
        """Update renderer for new screen dimensions."""
        pass


class IOverlay(ABC):
    """Abstract base class for UI overlays."""
    
    @abstractmethod
    def show(self) -> None:
        """Show the overlay."""
        pass
    
    @abstractmethod
    def hide(self) -> None:
        """Hide the overlay."""
        pass
    
    @abstractmethod
    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        pass
    
    @abstractmethod
    def handle_event(self, event: pg.event.Event) -> bool:
        """Handle event, return True if event was consumed."""
        pass
    
    @abstractmethod
    def render(self, surface: pg.Surface) -> None:
        """Render the overlay."""
        pass


class IResourceManager(ABC):
    """Abstract base class for resource management."""
    
    @abstractmethod
    def load_image(self, path: str) -> pg.Surface:
        """Load and cache an image."""
        pass
    
    @abstractmethod
    def load_sound(self, path: str) -> pg.mixer.Sound:
        """Load and cache a sound."""
        pass
    
    @abstractmethod
    def clear_cache(self) -> None:
        """Clear resource cache."""
        pass


class IAnimationState(ABC):
    """Abstract base class for animation states."""
    
    @abstractmethod
    def start(self) -> None:
        """Start the animation."""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the animation."""
        pass
    
    @abstractmethod
    def update(self, delta_time: float) -> pg.Surface:
        """Update and return current frame."""
        pass
    
    @property
    @abstractmethod
    def is_finished(self) -> bool:
        """Check if animation has finished."""
        pass