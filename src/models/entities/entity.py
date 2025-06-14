"""Entity model for non-character game objects."""
from __future__ import annotations

from typing import Optional
import pygame as pg

from src.models.entities.base_entity import StaticEntity
from src.core.exceptions import EntityError


class Entity(StaticEntity):
    """
    Generic entity class for non-character game objects.
    
    This class represents static game objects such as decorations,
    collectibles, obstacles, and other environmental elements.
    """
    
    def __init__(
        self,
        x: float,
        y: float,
        image_path: Optional[str] = None,
        image: Optional[pg.Surface] = None
    ) -> None:
        """
        Initialize entity at given position.
        
        Args:
            x: X coordinate in world space
            y: Y coordinate in world space
            image_path: Optional path to image file
            image: Optional pre-loaded image surface
            
        Raises:
            EntityError: If neither image_path nor image is provided
        """
        if image_path:
            image = self._load_image(image_path)
        elif image is None:
            raise EntityError("Entity requires either image_path or image")
        
        super().__init__(x, y, image)
        
        # Additional entity properties
        self._is_interactive = False
        self._is_collectible = False
        self._interaction_range = 50
        self._custom_data = {}
    
    @property
    def is_interactive(self) -> bool:
        """Check if entity can be interacted with."""
        return self._is_interactive
    
    @is_interactive.setter
    def is_interactive(self, value: bool) -> None:
        """Set whether entity is interactive."""
        self._is_interactive = value
    
    @property
    def is_collectible(self) -> bool:
        """Check if entity can be collected."""
        return self._is_collectible
    
    @is_collectible.setter
    def is_collectible(self, value: bool) -> None:
        """Set whether entity is collectible."""
        self._is_collectible = value
    
    @property
    def interaction_range(self) -> float:
        """Get interaction range in pixels."""
        return self._interaction_range
    
    @interaction_range.setter
    def interaction_range(self, value: float) -> None:
        """Set interaction range."""
        self._interaction_range = max(0, value)
    
    def can_interact_with(self, other_rect: pg.Rect) -> bool:
        """
        Check if another rectangle is within interaction range.
        
        Args:
            other_rect: Rectangle to check against
            
        Returns:
            True if within interaction range
        """
        if not self._is_interactive:
            return False
        
        # Create inflated rect for interaction range
        interaction_rect = self.rect.inflate(
            self._interaction_range * 2,
            self._interaction_range * 2
        )
        
        return interaction_rect.colliderect(other_rect)
    
    def interact(self) -> Optional[dict]:
        """
        Perform interaction with entity.
        
        Returns:
            Interaction result data or None
        """
        if not self._is_interactive:
            return None
        
        # Override in subclasses for specific interactions
        return {"type": "generic", "entity_id": id(self)}
    
    def collect(self) -> Optional[dict]:
        """
        Collect this entity.
        
        Returns:
            Collection result data or None
        """
        if not self._is_collectible:
            return None
        
        # Remove from all groups
        self.kill()
        
        # Return collection data
        return {"type": "collected", "entity_id": id(self)}
    
    def set_custom_data(self, key: str, value: any) -> None:
        """
        Set custom data for entity.
        
        Args:
            key: Data key
            value: Data value
        """
        self._custom_data[key] = value
    
    def get_custom_data(self, key: str, default: any = None) -> any:
        """
        Get custom data from entity.
        
        Args:
            key: Data key
            default: Default value if key not found
            
        Returns:
            Data value or default
        """
        return self._custom_data.get(key, default)
    
    def _load_image(self, path: str) -> pg.Surface:
        """
        Load image from file path.
        
        Args:
            path: Path to image file
            
        Returns:
            Loaded image surface
            
        Raises:
            EntityError: If image cannot be loaded
        """
        try:
            return pg.image.load(path).convert_alpha()
        except pg.error as e:
            raise EntityError(f"Failed to load entity image {path}: {e}")


class CollectibleEntity(Entity):
    """Specialized entity for collectible items."""
    
    def __init__(
        self,
        x: float,
        y: float,
        image: pg.Surface,
        item_type: str,
        value: int = 1
    ) -> None:
        """
        Initialize collectible entity.
        
        Args:
            x: X coordinate
            y: Y coordinate
            image: Entity image
            item_type: Type of collectible (coin, health, etc.)
            value: Value when collected
        """
        super().__init__(x, y, image=image)
        
        self.is_collectible = True
        self._item_type = item_type
        self._value = value
        
        # Animation properties
        self._bob_offset = 0.0
        self._bob_speed = 2.0
        self._bob_amplitude = 5.0
        self._time_alive = 0.0
    
    @property
    def item_type(self) -> str:
        """Get collectible type."""
        return self._item_type
    
    @property
    def value(self) -> int:
        """Get collectible value."""
        return self._value
    
    def update(self, delta_time: float) -> None:
        """
        Update collectible animation.
        
        Args:
            delta_time: Time since last update
        """
        self._time_alive += delta_time
        
        # Apply bobbing animation
        self._bob_offset = (
            self._bob_amplitude * 
            pg.math.sin(self._time_alive * self._bob_speed)
        )
        
        # Update visual position (not collision rect)
        # This would be used by renderer for drawing offset
        self.set_custom_data("render_offset_y", self._bob_offset)
    
    def collect(self) -> Optional[dict]:
        """
        Collect this item.
        
        Returns:
            Collection data including type and value
        """
        self.kill()
        
        return {
            "type": "collected",
            "item_type": self._item_type,
            "value": self._value
        }


class InteractableEntity(Entity):
    """Specialized entity for interactable objects."""
    
    def __init__(
        self,
        x: float,
        y: float,
        image: pg.Surface,
        interaction_type: str,
        interaction_data: Optional[dict] = None
    ) -> None:
        """
        Initialize interactable entity.
        
        Args:
            x: X coordinate
            y: Y coordinate
            image: Entity image
            interaction_type: Type of interaction
            interaction_data: Additional interaction data
        """
        super().__init__(x, y, image=image)
        
        self.is_interactive = True
        self._interaction_type = interaction_type
        self._interaction_data = interaction_data or {}
        self._interaction_cooldown = 0.0
        self._cooldown_duration = 1.0
    
    def update(self, delta_time: float) -> None:
        """Update interaction cooldown."""
        if self._interaction_cooldown > 0:
            self._interaction_cooldown = max(0, self._interaction_cooldown - delta_time)
    
    def interact(self) -> Optional[dict]:
        """
        Perform interaction.
        
        Returns:
            Interaction result or None if on cooldown
        """
        if self._interaction_cooldown > 0:
            return None
        
        self._interaction_cooldown = self._cooldown_duration
        
        return {
            "type": self._interaction_type,
            "data": self._interaction_data.copy()
        }