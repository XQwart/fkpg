"""Base entity model for all game objects."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
import pygame as pg

from src.core.interfaces import IEntity


class BaseEntity(pg.sprite.Sprite, IEntity):
    """Abstract base class for all game entities."""
    
    def __init__(self) -> None:
        """Initialize base entity."""
        super().__init__()
        self._position = pg.math.Vector2()
        self._velocity = pg.math.Vector2()
        self._image: Optional[pg.Surface] = None
        self._rect: Optional[pg.Rect] = None
    
    @property
    def position(self) -> pg.math.Vector2:
        """Get entity position."""
        return self._position
    
    @position.setter
    def position(self, value: pg.math.Vector2) -> None:
        """Set entity position and update rect."""
        self._position = value
        if self._rect:
            self._rect.center = (int(value.x), int(value.y))
    
    @property
    def velocity(self) -> pg.math.Vector2:
        """Get entity velocity."""
        return self._velocity
    
    @velocity.setter
    def velocity(self, value: pg.math.Vector2) -> None:
        """Set entity velocity."""
        self._velocity = value
    
    @property
    def image(self) -> Optional[pg.Surface]:
        """Get entity image for rendering."""
        return self._image
    
    @image.setter
    def image(self, value: pg.Surface) -> None:
        """Set entity image and create/update rect."""
        self._image = value
        if value:
            if self._rect:
                center = self._rect.center
                self._rect = value.get_rect(center=center)
            else:
                self._rect = value.get_rect(center=(int(self._position.x), int(self._position.y)))
    
    @property
    def rect(self) -> pg.Rect:
        """Get entity bounding rectangle."""
        if self._rect is None:
            # Create a default rect if none exists
            self._rect = pg.Rect(int(self._position.x), int(self._position.y), 1, 1)
        return self._rect
    
    @abstractmethod
    def update(self, delta_time: float) -> None:
        """Update entity state. Must be implemented by subclasses."""
        pass
    
    def kill(self) -> None:
        """Remove entity from all sprite groups."""
        super().kill()


class StaticEntity(BaseEntity):
    """Base class for static, non-moving entities."""
    
    def __init__(self, x: float, y: float, image: pg.Surface) -> None:
        """Initialize static entity at given position."""
        super().__init__()
        self.position = pg.math.Vector2(x, y)
        self.image = image
    
    def update(self, delta_time: float) -> None:
        """Static entities don't need updates."""
        pass


class DynamicEntity(BaseEntity):
    """Base class for moving entities with physics."""
    
    def __init__(self) -> None:
        """Initialize dynamic entity."""
        super().__init__()
        self._acceleration = pg.math.Vector2()
        self._max_velocity = pg.math.Vector2(float('inf'), float('inf'))
    
    @property
    def acceleration(self) -> pg.math.Vector2:
        """Get entity acceleration."""
        return self._acceleration
    
    @acceleration.setter
    def acceleration(self, value: pg.math.Vector2) -> None:
        """Set entity acceleration."""
        self._acceleration = value
    
    @property
    def max_velocity(self) -> pg.math.Vector2:
        """Get maximum velocity constraints."""
        return self._max_velocity
    
    @max_velocity.setter
    def max_velocity(self, value: pg.math.Vector2) -> None:
        """Set maximum velocity constraints."""
        self._max_velocity = value
    
    def update_physics(self, delta_time: float) -> None:
        """Update entity physics (velocity and position)."""
        # Update velocity based on acceleration
        self._velocity += self._acceleration * delta_time
        
        # Clamp velocity to maximum values
        if abs(self._velocity.x) > abs(self._max_velocity.x):
            self._velocity.x = self._max_velocity.x if self._velocity.x > 0 else -self._max_velocity.x
        
        if abs(self._velocity.y) > abs(self._max_velocity.y):
            self._velocity.y = self._max_velocity.y if self._velocity.y > 0 else -self._max_velocity.y
        
        # Update position based on velocity
        self.position += self._velocity * delta_time