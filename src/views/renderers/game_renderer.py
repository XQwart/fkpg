"""Game world renderer with camera and HUD."""
from __future__ import annotations

from typing import List, Optional, Dict, Tuple
import pygame as pg

from src.views.camera import Camera
from src.views.ui.hud import HUDRenderer
from src.models.entities.player import Player
from src.models.world.level import Level, Tile
from src.core.interfaces import IRenderer
from src.core.cache_manager import get_cache_manager


class GameRenderer(IRenderer):
    """Renders the game world, entities, and UI."""
    
    def __init__(self) -> None:
        """Initialize game renderer."""
        self._screen: Optional[pg.Surface] = None
        self._camera: Optional[Camera] = None
        self._hud_renderer = HUDRenderer()
        self._debug_mode = False
        self._cache_manager = get_cache_manager()
    
    def initialize(self, screen: pg.Surface) -> None:
        """Initialize renderer with screen surface."""
        self._screen = screen
        self._camera = Camera(screen.get_width(), screen.get_height())
    
    @property
    def camera(self) -> Camera:
        """Get camera instance."""
        if not self._camera:
            raise RuntimeError("Renderer not initialized")
        return self._camera
    
    def toggle_debug_mode(self) -> None:
        """Toggle debug rendering mode."""
        self._debug_mode = not self._debug_mode
    
    def render(
        self,
        surface: pg.Surface,
        level: Level,
        entities: pg.sprite.Group,
        player: Player
    ) -> None:
        """
        Render complete game view.
        
        Args:
            surface: Surface to render to
            level: Current level
            entities: All game entities
            player: Player entity
        """
        if not self._camera:
            self.initialize(surface)
        
        # Clear screen with level background color
        surface.fill(level.background_color)
        
        # Get camera viewport
        camera_rect = self._camera.viewport
        
        # Render level tiles
        self._render_level(surface, level, camera_rect)
        
        # Render entities
        self._render_entities(surface, entities)
        
        # Render debug info if enabled
        if self._debug_mode:
            self._render_debug(surface, player, entities)
        
        # Render HUD (always on top)
        self._hud_renderer.render(surface, player)
    
    def update_screen_size(self, width: int, height: int) -> None:
        """Update renderer for new screen dimensions."""
        if self._camera:
            self._camera.update_viewport_size(width, height)
        self._hud_renderer.update_screen_size(width, height)
    
    def _render_level(self, surface: pg.Surface, level: Level, camera_rect: pg.Rect) -> None:
        """Render visible level tiles."""
        # Get visible tiles
        visible_tiles = level.get_visible_tiles(camera_rect)
        
        # Sort by layer order (if needed)
        # For now, just render all tiles
        for tile, layer in visible_tiles:
            screen_rect = self._camera.apply_to_entity(tile)
            
            # Apply layer opacity if needed
            if layer.opacity < 1.0:
                cache_key = (tile.tile_id or id(tile.image), layer.opacity)
                
                # Try to get from cache
                tile_surface = self._cache_manager.get("tile_surfaces", cache_key)
                
                if tile_surface is None:
                    # Create and cache the surface
                    tile_surface = tile.image.copy()
                    tile_surface.set_alpha(int(255 * layer.opacity))
                    self._cache_manager.put("tile_surfaces", cache_key, tile_surface)
                
                surface.blit(tile_surface, screen_rect)
            else:
                surface.blit(tile.image, screen_rect)
            
            # Debug: Show tile properties
            if self._debug_mode:
                if tile.is_collidable:
                    pg.draw.rect(surface, (255, 0, 0), screen_rect, 1)
                elif tile.is_hazardous:
                    pg.draw.rect(surface, (255, 255, 0), screen_rect, 1)
                elif tile.is_platform:
                    pg.draw.rect(surface, (0, 255, 0), screen_rect, 1)
    
    def _render_entities(self, surface: pg.Surface, entities: pg.sprite.Group) -> None:
        """Render all visible entities."""
        for entity in entities:
            # Only render if visible
            if self._camera.is_visible(entity.rect):
                screen_rect = self._camera.apply_to_entity(entity)
                surface.blit(entity.image, screen_rect)
                
                # Debug: Show entity bounds
                if self._debug_mode:
                    pg.draw.rect(surface, (0, 255, 255), screen_rect, 1)
    
    def _render_debug(self, surface: pg.Surface, player: Player, entities: pg.sprite.Group) -> None:
        """Render debug information."""
        debug_font = pg.font.Font(None, 20)
        
        # Get cache stats
        cache_stats = self._cache_manager.get_stats()
        total_cache_memory = cache_stats["total_memory"] / (1024 * 1024)  # Convert to MB
        
        debug_info = [
            f"FPS: {int(pg.time.Clock().get_fps())}",
            f"Player Pos: ({int(player.position.x)}, {int(player.position.y)})",
            f"Player Vel: ({player.velocity.x:.1f}, {player.velocity.y:.1f})",
            f"On Ground: {player.on_ground}",
            f"State: {player.current_state.name}",
            f"Entities: {len(entities)}",
            f"Camera: ({int(self._camera.position.x)}, {int(self._camera.position.y)})",
            f"Cache Memory: {total_cache_memory:.1f} MB"
        ]
        
        y = 10
        for line in debug_info:
            text = debug_font.render(line, True, (255, 255, 255))
            text_bg = pg.Surface((text.get_width() + 4, text.get_height() + 2))
            text_bg.fill((0, 0, 0))
            text_bg.set_alpha(128)
            surface.blit(text_bg, (surface.get_width() - text.get_width() - 12, y - 1))
            surface.blit(text, (surface.get_width() - text.get_width() - 10, y))
            y += 22