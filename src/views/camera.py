"""Camera system for following entities and rendering viewports."""
from __future__ import annotations

from typing import Optional
import pygame as pg

from src.core.constants import CAMERA_LERP_FACTOR
from src.models.entities.base_entity import BaseEntity


class Camera:
    """Smooth-following camera with viewport management."""
    
    def __init__(self, viewport_width: int, viewport_height: int) -> None:
        """
        Initialize camera with viewport dimensions.
        
        Args:
            viewport_width: Width of the camera viewport
            viewport_height: Height of the camera viewport
        """
        self._viewport = pg.Rect(0, 0, viewport_width, viewport_height)
        self._position = pg.math.Vector2()
        self._target_position = pg.math.Vector2()
        self._world_bounds: Optional[pg.Rect] = None
        self._lerp_factor = CAMERA_LERP_FACTOR
        self._follow_target: Optional[BaseEntity] = None
    
    @property
    def position(self) -> pg.math.Vector2:
        """Get current camera position (top-left corner)."""
        return self._position.copy()
    
    @property
    def center(self) -> pg.math.Vector2:
        """Get current camera center position."""
        return self._position + pg.math.Vector2(self._viewport.width / 2, self._viewport.height / 2)
    
    @property
    def viewport(self) -> pg.Rect:
        """Get camera viewport rectangle in world coordinates."""
        return pg.Rect(
            int(self._position.x),
            int(self._position.y),
            self._viewport.width,
            self._viewport.height
        )
    
    @property
    def lerp_factor(self) -> float:
        """Get camera smoothing factor."""
        return self._lerp_factor
    
    @lerp_factor.setter
    def lerp_factor(self, value: float) -> None:
        """Set camera smoothing factor (0.0 to 1.0)."""
        self._lerp_factor = max(0.0, min(1.0, value))
    
    def set_world_bounds(self, bounds: Optional[pg.Rect]) -> None:
        """
        Set world boundaries for camera movement.
        
        Args:
            bounds: World boundary rectangle or None for no bounds
        """
        self._world_bounds = bounds.copy() if bounds else None
    
    def set_follow_target(self, target: Optional[BaseEntity]) -> None:
        """
        Set entity for camera to follow.
        
        Args:
            target: Entity to follow or None to stop following
        """
        self._follow_target = target
        
        if target:
            # Immediately center on target
            self._center_on_position(target.position)
    
    def update_viewport_size(self, width: int, height: int) -> None:
        """
        Update camera viewport dimensions.
        
        Args:
            width: New viewport width
            height: New viewport height
        """
        old_center = self.center
        self._viewport.width = width
        self._viewport.height = height
        
        # Maintain center position
        self._position = old_center - pg.math.Vector2(width / 2, height / 2)
        self._constrain_to_bounds()
    
    def update(self, delta_time: float) -> None:
        """
        Update camera position.
        
        Args:
            delta_time: Time elapsed since last update
        """
        if self._follow_target:
            # Calculate desired position to center on target
            desired_center = self._follow_target.position
            desired_position = desired_center - pg.math.Vector2(
                self._viewport.width / 2,
                self._viewport.height / 2
            )
            
            # Smooth interpolation to desired position
            self._position += (desired_position - self._position) * self._lerp_factor
            
            # Constrain to world bounds
            self._constrain_to_bounds()
    
    def apply_to_position(self, world_position: pg.math.Vector2) -> pg.math.Vector2:
        """
        Convert world position to screen position.
        
        Args:
            world_position: Position in world coordinates
            
        Returns:
            Position in screen coordinates
        """
        return world_position - self._position
    
    def apply_to_rect(self, world_rect: pg.Rect) -> pg.Rect:
        """
        Convert world rectangle to screen rectangle.
        
        Args:
            world_rect: Rectangle in world coordinates
            
        Returns:
            Rectangle in screen coordinates
        """
        return world_rect.move(-int(self._position.x), -int(self._position.y))
    
    def apply_to_entity(self, entity: BaseEntity) -> pg.Rect:
        """
        Get entity's screen rectangle.
        
        Args:
            entity: Entity to convert
            
        Returns:
            Entity rectangle in screen coordinates
        """
        return self.apply_to_rect(entity.rect)
    
    def screen_to_world(self, screen_position: pg.math.Vector2) -> pg.math.Vector2:
        """
        Convert screen position to world position.
        
        Args:
            screen_position: Position in screen coordinates
            
        Returns:
            Position in world coordinates
        """
        return screen_position + self._position
    
    def is_visible(self, world_rect: pg.Rect) -> bool:
        """
        Check if world rectangle is visible in camera viewport.
        
        Args:
            world_rect: Rectangle in world coordinates
            
        Returns:
            True if any part of rectangle is visible
        """
        return self.viewport.colliderect(world_rect)
    
    def set_position(self, position: pg.math.Vector2) -> None:
        """
        Set camera position directly.
        
        Args:
            position: New camera position (top-left corner)
        """
        self._position = position.copy()
        self._constrain_to_bounds()
    
    def center_on_position(self, position: pg.math.Vector2) -> None:
        """
        Center camera on specific world position.
        
        Args:
            position: World position to center on
        """
        self._center_on_position(position)
    
    def move(self, offset: pg.math.Vector2) -> None:
        """
        Move camera by offset.
        
        Args:
            offset: Movement offset
        """
        self._position += offset
        self._constrain_to_bounds()
    
    def shake(self, intensity: float, duration: float) -> None:
        """
        Apply camera shake effect.
        
        Args:
            intensity: Shake intensity in pixels
            duration: Shake duration in seconds
        """
        # TODO: Implement camera shake
        pass
    
    def _center_on_position(self, position: pg.math.Vector2) -> None:
        """Center camera on given position."""
        self._position = position - pg.math.Vector2(
            self._viewport.width / 2,
            self._viewport.height / 2
        )
        self._constrain_to_bounds()
    
    def _constrain_to_bounds(self) -> None:
        """Constrain camera position to world bounds."""
        if not self._world_bounds:
            return
        
        # Ensure camera doesn't show outside world bounds
        if self._viewport.width >= self._world_bounds.width:
            # Center camera if viewport is larger than world
            self._position.x = self._world_bounds.centerx - self._viewport.width / 2
        else:
            # Constrain to bounds
            self._position.x = max(
                self._world_bounds.left,
                min(self._position.x, self._world_bounds.right - self._viewport.width)
            )
        
        if self._viewport.height >= self._world_bounds.height:
            # Center camera if viewport is larger than world
            self._position.y = self._world_bounds.centery - self._viewport.height / 2
        else:
            # Constrain to bounds
            self._position.y = max(
                self._world_bounds.top,
                min(self._position.y, self._world_bounds.bottom - self._viewport.height)
            )