"""Tile model for level building blocks."""
from __future__ import annotations

from typing import Optional, Dict, Any
from dataclasses import dataclass
import pygame as pg

from src.models.entities.abstract_entity import StaticEntity


@dataclass
class TileProperties:
    """Properties defining tile behavior and characteristics."""
    
    collidable: bool = True
    hazardous: bool = False
    platform: bool = False  # One-way platform
    slippery: bool = False
    destructible: bool = False
    animated: bool = False
    trigger: Optional[str] = None  # Trigger ID for special tiles
    damage: int = 0  # Damage dealt if hazardous
    friction: float = 1.0  # Surface friction multiplier
    bounce: float = 0.0  # Bounce factor (0-1)
    
    @classmethod
    def from_tmx_properties(cls, properties: Dict[str, Any]) -> TileProperties:
        """
        Create tile properties from TMX tile properties.
        
        Args:
            properties: Dictionary of TMX properties
            
        Returns:
            TileProperties instance
        """
        return cls(
            collidable=properties.get('collidable', True),
            hazardous=properties.get('hazardous', False),
            platform=properties.get('platform', False),
            slippery=properties.get('slippery', False),
            destructible=properties.get('destructible', False),
            animated=properties.get('animated', False),
            trigger=properties.get('trigger'),
            damage=int(properties.get('damage', 0)),
            friction=float(properties.get('friction', 1.0)),
            bounce=float(properties.get('bounce', 0.0))
        )


class Tile(StaticEntity):
    """Single tile in the game world."""
    
    def __init__(
        self,
        grid_x: int,
        grid_y: int,
        tile_size: int,
        image: pg.Surface,
        properties: Optional[TileProperties] = None,
        tile_id: Optional[int] = None
    ) -> None:
        """
        Initialize tile at grid position.
        
        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            tile_size: Size of tile in pixels
            image: Tile image surface
            properties: Tile properties
            tile_id: Optional tile ID from tileset
        """
        # Calculate world position from grid position
        world_x = grid_x * tile_size
        world_y = grid_y * tile_size
        
        super().__init__(world_x, world_y, image)
        
        self._grid_x = grid_x
        self._grid_y = grid_y
        self._tile_size = tile_size
        self._tile_id = tile_id
        self._properties = properties or TileProperties()
        
        # Animation state if animated
        self._animation_frames: list[pg.Surface] = []
        self._current_frame = 0
        self._animation_speed = 0.1
        self._animation_timer = 0.0
    
    @property
    def grid_position(self) -> tuple[int, int]:
        """Get tile grid coordinates."""
        return (self._grid_x, self._grid_y)
    
    @property
    def properties(self) -> TileProperties:
        """Get tile properties."""
        return self._properties
    
    @property
    def tile_id(self) -> Optional[int]:
        """Get tile ID from tileset."""
        return self._tile_id
    
    @property
    def is_collidable(self) -> bool:
        """Check if tile blocks movement."""
        return self._properties.collidable
    
    @property
    def is_hazardous(self) -> bool:
        """Check if tile causes damage."""
        return self._properties.hazardous
    
    @property
    def is_platform(self) -> bool:
        """Check if tile is a one-way platform."""
        return self._properties.platform
    
    @property
    def is_slippery(self) -> bool:
        """Check if tile has reduced friction."""
        return self._properties.slippery
    
    @property
    def is_destructible(self) -> bool:
        """Check if tile can be destroyed."""
        return self._properties.destructible
    
    @property
    def trigger_id(self) -> Optional[str]:
        """Get trigger ID if tile is a trigger."""
        return self._properties.trigger
    
    def add_animation_frame(self, frame: pg.Surface) -> None:
        """
        Add animation frame for animated tiles.
        
        Args:
            frame: Animation frame surface
        """
        self._animation_frames.append(frame)
        self._properties.animated = True
    
    def set_animation_speed(self, speed: float) -> None:
        """
        Set animation playback speed.
        
        Args:
            speed: Seconds per frame
        """
        self._animation_speed = max(0.01, speed)
    
    def update(self, delta_time: float) -> None:
        """
        Update animated tile.
        
        Args:
            delta_time: Time since last update
        """
        if not self._properties.animated or not self._animation_frames:
            return
        
        self._animation_timer += delta_time
        
        if self._animation_timer >= self._animation_speed:
            self._animation_timer = 0.0
            self._current_frame = (self._current_frame + 1) % len(self._animation_frames)
            self.image = self._animation_frames[self._current_frame]
    
    def take_damage(self, amount: int) -> bool:
        """
        Apply damage to destructible tile.
        
        Args:
            amount: Damage amount
            
        Returns:
            True if tile was destroyed
        """
        if not self._properties.destructible:
            return False
        
        # Simple destruction - remove tile
        # Could be extended with health system
        self.kill()
        return True
    
    def get_friction_multiplier(self) -> float:
        """Get friction multiplier for movement calculations."""
        return self._properties.friction
    
    def get_bounce_factor(self) -> float:
        """Get bounce factor for collision response."""
        return self._properties.bounce
    
    def get_damage(self) -> int:
        """Get damage amount for hazardous tiles."""
        return self._properties.damage if self._properties.hazardous else 0


class AnimatedTile(Tile):
    """Specialized tile with built-in animation support."""
    
    def __init__(
        self,
        grid_x: int,
        grid_y: int,
        tile_size: int,
        frames: list[pg.Surface],
        frame_duration: float = 0.1,
        properties: Optional[TileProperties] = None,
        tile_id: Optional[int] = None
    ) -> None:
        """
        Initialize animated tile.
        
        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            tile_size: Size of tile in pixels
            frames: List of animation frames
            frame_duration: Seconds per frame
            properties: Tile properties
            tile_id: Optional tile ID
        """
        if not frames:
            raise ValueError("AnimatedTile requires at least one frame")
        
        # Initialize with first frame
        super().__init__(grid_x, grid_y, tile_size, frames[0], properties, tile_id)
        
        # Set up animation
        self._animation_frames = frames
        self.set_animation_speed(frame_duration)
        self._properties.animated = True


class TriggerTile(Tile):
    """Specialized tile that triggers events."""
    
    def __init__(
        self,
        grid_x: int,
        grid_y: int,
        tile_size: int,
        image: pg.Surface,
        trigger_id: str,
        trigger_data: Optional[dict] = None,
        properties: Optional[TileProperties] = None,
        tile_id: Optional[int] = None
    ) -> None:
        """
        Initialize trigger tile.
        
        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            tile_size: Size of tile in pixels
            image: Tile image surface
            trigger_id: Trigger identifier
            trigger_data: Additional trigger data
            properties: Tile properties
            tile_id: Optional tile ID
        """
        if properties is None:
            properties = TileProperties()
        properties.trigger = trigger_id
        
        super().__init__(grid_x, grid_y, tile_size, image, properties, tile_id)
        
        self._trigger_data = trigger_data or {}
        self._triggered = False
        self._repeatable = self._trigger_data.get('repeatable', True)
    
    @property
    def trigger_data(self) -> dict:
        """Get trigger data."""
        return self._trigger_data.copy()
    
    @property
    def is_triggered(self) -> bool:
        """Check if trigger has been activated."""
        return self._triggered
    
    def activate(self) -> Optional[dict]:
        """
        Activate trigger.
        
        Returns:
            Trigger activation data or None if already triggered
        """
        if self._triggered and not self._repeatable:
            return None
        
        self._triggered = True
        
        return {
            'trigger_id': self._properties.trigger,
            'position': self.grid_position,
            'data': self._trigger_data.copy()
        }
    
    def reset(self) -> None:
        """Reset trigger to untriggered state."""
        self._triggered = False