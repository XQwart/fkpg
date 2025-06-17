"""Character model for game characters."""
from __future__ import annotations

from abc import ABC
from typing import Optional
from pathlib import Path
import pygame as pg

from src.models.entities.abstract_entity import DynamicEntity
from src.core.exceptions import ResourceError


class Character(DynamicEntity, ABC):
    """Base class for all game characters (player, NPCs, enemies)."""
    
    def __init__(
        self,
        x: float,
        y: float,
        max_health: int = 100,
        sprite_size: tuple[int, int] = (128, 128)
    ) -> None:
        """Initialize character at given position."""
        super().__init__()
        
        # Position
        self.position = pg.math.Vector2(x, y)
        
        # Health system
        self._max_health = max_health
        self._health = max_health
        self._is_alive = True
        
        # Sprite properties
        self._sprite_size = sprite_size
        self._facing_left = False
        
        # Physics properties
        self._on_ground = False
        
        # Invulnerability
        self._invulnerable = False
        self._invulnerable_timer = 0.0
        self._invulnerable_duration = 1.0  # 1 second of invulnerability after hit
    
    # Health properties
    @property
    def health(self) -> int:
        """Get current health."""
        return self._health
    
    @property
    def max_health(self) -> int:
        """Get maximum health."""
        return self._max_health
    
    @property
    def health_percentage(self) -> float:
        """Get health as percentage (0.0 to 1.0)."""
        return self._health / self._max_health if self._max_health > 0 else 0.0
    
    @property
    def is_alive(self) -> bool:
        """Check if character is alive."""
        return self._is_alive
    
    @property
    def is_invulnerable(self) -> bool:
        """Check if character is currently invulnerable."""
        return self._invulnerable
    
    # Physics properties
    @property
    def on_ground(self) -> bool:
        """Check if character is on ground."""
        return self._on_ground
    
    @on_ground.setter
    def on_ground(self, value: bool) -> None:
        """Set ground state."""
        self._on_ground = value
    
    @property
    def facing_left(self) -> bool:
        """Check if character is facing left."""
        return self._facing_left
    
    @facing_left.setter
    def facing_left(self, value: bool) -> None:
        """Set facing direction."""
        self._facing_left = value
    
    # Health methods
    def take_damage(self, amount: int) -> bool:
        """
        Apply damage to character.
        
        Args:
            amount: Damage amount to apply
            
        Returns:
            True if damage was applied, False if invulnerable
        """
        if self._invulnerable or not self._is_alive:
            return False
        
        self._health = max(0, self._health - amount)
        
        if self._health <= 0:
            self._health = 0
            self._is_alive = False
            self._on_death()
        else:
            self._invulnerable = True
            self._invulnerable_timer = self._invulnerable_duration
            self._on_damage(amount)
        
        return True
    
    def heal(self, amount: int) -> int:
        """
        Heal character.
        
        Args:
            amount: Health amount to restore
            
        Returns:
            Actual amount healed
        """
        if not self._is_alive:
            return 0
        
        old_health = self._health
        self._health = min(self._max_health, self._health + amount)
        return self._health - old_health
    
    def set_invulnerable(self, duration: float) -> None:
        """Set character as invulnerable for specified duration."""
        self._invulnerable = True
        self._invulnerable_timer = duration
    
    # Update method
    def update(self, delta_time: float) -> None:
        """Update character state."""
        # Update invulnerability timer
        if self._invulnerable and self._invulnerable_timer > 0:
            self._invulnerable_timer -= delta_time
            if self._invulnerable_timer <= 0:
                self._invulnerable = False
                self._invulnerable_timer = 0
        
        # Update physics
        self.update_physics(delta_time)
        
        # Character-specific updates
        self._update_character(delta_time)
    
    # Protected methods for subclasses
    def _update_character(self, delta_time: float) -> None:
        """Character-specific update logic. Override in subclasses."""
        pass
    
    def _on_damage(self, amount: int) -> None:
        """Called when character takes damage. Override for specific behavior."""
        pass
    
    def _on_death(self) -> None:
        """Called when character dies. Override for specific behavior."""
        pass
    
    # Utility methods
    @staticmethod
    def load_sprite(path: Path, size: tuple[int, int]) -> pg.Surface:
        """
        Load and scale a sprite image.
        
        Args:
            path: Path to sprite image
            size: Target size for scaling
            
        Returns:
            Scaled sprite surface
            
        Raises:
            ResourceError: If sprite cannot be loaded
        """
        if not path.exists():
            # Create placeholder sprite
            surface = pg.Surface(size, pg.SRCALPHA)
            surface.fill((255, 0, 255))  # Magenta for missing sprites
            return surface
        
        try:
            sprite = pg.image.load(str(path)).convert_alpha()
            return pg.transform.scale(sprite, size)
        except pg.error as e:
            raise ResourceError(f"Failed to load sprite {path}: {e}")