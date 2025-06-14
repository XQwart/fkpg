"""HUD (Heads-Up Display) view for player interface."""
from __future__ import annotations

from typing import Optional
from pathlib import Path
import pygame as pg

from src.models.entities.player import Player
from src.core.constants import UIConstants, AssetPaths, PlayerConstants
from src.core.interfaces import IRenderer
from src.core.exceptions import ResourceError


class HUDRenderer(IRenderer):
    """Renders player HUD with health, mana, and resources."""
    
    def __init__(self) -> None:
        """Initialize HUD renderer."""
        self._screen: Optional[pg.Surface] = None
        self._font: Optional[pg.font.Font] = None
        self._assets_loaded = False
        
        # Cached surfaces
        self._hud_bg_surface: Optional[pg.Surface] = None
        
        # Asset surfaces
        self._portrait: Optional[pg.Surface] = None
        self._heart_full: Optional[pg.Surface] = None
        self._heart_empty: Optional[pg.Surface] = None
        self._coin_icon: Optional[pg.Surface] = None
        self._mana_icon: Optional[pg.Surface] = None
        
        # Pre-calculated positions (updated on screen resize)
        self._hud_rect = pg.Rect(0, 0, UIConstants.HUD_WIDTH, UIConstants.HUD_HEIGHT)
        self._portrait_rect = pg.Rect(0, 0, *UIConstants.PORTRAIT_SIZE)
        self._hearts_rect = pg.Rect(0, 0, 0, UIConstants.HEART_SIZE[1])
        self._coin_rect = pg.Rect(0, 0, 100, 30)
        self._mana_bar_rect = pg.Rect(0, 0, 0, 20)
    
    def render(self, surface: pg.Surface, player: Optional[Player] = None) -> None:
        """
        Render HUD to surface.
        
        Args:
            surface: Surface to render to
            player: Player entity to display stats for
        """
        if not player:
            return
        
        # Ensure assets are loaded
        if not self._assets_loaded:
            self._load_assets()
            self._screen = surface
            self.update_screen_size(surface.get_width(), surface.get_height())
        
        # Draw HUD background
        self._draw_hud_background(surface)
        
        # Draw portrait
        self._draw_portrait(surface)
        
        # Draw health hearts
        self._draw_health(surface, player)
        
        # Draw coin counter
        self._draw_coins(surface, player)
        
        # Draw mana bar
        self._draw_mana(surface, player)
    
    def update_screen_size(self, width: int, height: int) -> None:
        """Update renderer for new screen dimensions."""
        # Update HUD position (top-left with padding)
        self._hud_rect.topleft = (UIConstants.HUD_PADDING, UIConstants.HUD_PADDING)
        self._hud_rect.size = (UIConstants.HUD_WIDTH, UIConstants.HUD_HEIGHT)
        
        # Update portrait position
        self._portrait_rect.topleft = (
            self._hud_rect.x + 15,
            self._hud_rect.y + 15
        )
        
        # Update hearts position
        hearts_x = self._portrait_rect.right + 20
        hearts_y = self._portrait_rect.top
        hearts_width = (UIConstants.HEART_SIZE[0] + 2) * PlayerConstants.MAX_HEARTS_DISPLAY
        self._hearts_rect = pg.Rect(hearts_x, hearts_y, hearts_width, UIConstants.HEART_SIZE[1])
        
        # Update coin counter position
        self._coin_rect.topleft = (
            self._portrait_rect.left,
            self._portrait_rect.bottom + 15
        )
        
        # Update mana bar position
        self._mana_bar_rect = pg.Rect(
            hearts_x,
            hearts_y + UIConstants.HEART_SIZE[1] + 15,
            hearts_width,
            20
        )
        
        # Recreate cached HUD BG surface
        self._generate_hud_background()
    
    def _load_assets(self) -> None:
        """Load HUD assets."""
        try:
            # Initialize font
            self._font = pg.font.Font(None, UIConstants.FONT_SIZE_HUD)
            
            # Load images
            hud_path = Path(AssetPaths.HUD_ROOT)
            self._portrait = self._load_and_scale(
                hud_path / "portrait.png",
                UIConstants.PORTRAIT_SIZE
            )
            self._heart_full = self._load_and_scale(
                hud_path / "heart_full.png",
                UIConstants.HEART_SIZE
            )
            self._heart_empty = self._load_and_scale(
                hud_path / "heart_empty.png",
                UIConstants.HEART_SIZE
            )
            self._coin_icon = self._load_and_scale(
                hud_path / "coin.png",
                UIConstants.ICON_SIZE
            )
            self._mana_icon = self._load_and_scale(
                hud_path / "mana.png",
                UIConstants.ICON_SIZE
            )
            
            self._assets_loaded = True
            
        except Exception:
            # Create placeholder assets if loading fails
            self._create_placeholder_assets()
            self._assets_loaded = True
    
    def _load_and_scale(self, path: Path, size: tuple[int, int]) -> pg.Surface:
        """Load and scale an image asset."""
        if not path.exists():
            raise ResourceError(f"Asset not found: {path}")
        
        image = pg.image.load(str(path)).convert_alpha()
        return pg.transform.scale(image, size)
    
    def _create_placeholder_assets(self) -> None:
        """Create placeholder assets for missing files."""
        # Initialize font if not already
        if not self._font:
            self._font = pg.font.Font(None, UIConstants.FONT_SIZE_HUD)
        
        # Portrait placeholder
        self._portrait = pg.Surface(UIConstants.PORTRAIT_SIZE, pg.SRCALPHA)
        pg.draw.rect(self._portrait, (100, 100, 150), (0, 0, *UIConstants.PORTRAIT_SIZE))
        pg.draw.circle(self._portrait, (200, 180, 150), (32, 25), 15)
        pg.draw.rect(self._portrait, (100, 100, 150), (20, 40, 24, 24))
        
        # Heart placeholders
        self._heart_full = self._create_heart_shape((255, 0, 0), filled=True)
        self._heart_empty = self._create_heart_shape((80, 0, 0), filled=False)
        
        # Coin placeholder
        self._coin_icon = pg.Surface(UIConstants.ICON_SIZE, pg.SRCALPHA)
        pg.draw.circle(self._coin_icon, (255, 215, 0), (12, 12), 10)
        pg.draw.circle(self._coin_icon, (200, 150, 0), (12, 12), 10, 2)
        
        # Mana placeholder
        self._mana_icon = pg.Surface(UIConstants.ICON_SIZE, pg.SRCALPHA)
        pg.draw.circle(self._mana_icon, (0, 0, 255), (12, 12), 10)
        pg.draw.circle(self._mana_icon, (100, 100, 255), (12, 12), 6)
    
    def _create_heart_shape(self, color: tuple[int, int, int], filled: bool) -> pg.Surface:
        """Create a heart-shaped surface."""
        surface = pg.Surface(UIConstants.HEART_SIZE, pg.SRCALPHA)
        points = [
            (12, 6), (6, 0), (0, 6), (0, 12),
            (12, 24), (24, 12), (24, 6), (18, 0)
        ]
        
        if filled:
            pg.draw.polygon(surface, color, points)
        else:
            pg.draw.polygon(surface, color, points, 2)
        
        return surface
    
    def _generate_hud_background(self) -> None:
        """Generate semi-transparent HUD background surface once."""
        self._hud_bg_surface = pg.Surface(self._hud_rect.size, pg.SRCALPHA)
        pg.draw.rect(
            self._hud_bg_surface,
            (0, 0, 0, 150),
            (0, 0, *self._hud_rect.size),
            border_radius=10
        )
    
    def _draw_hud_background(self, surface: pg.Surface) -> None:
        """Blit cached HUD background."""
        if not self._hud_bg_surface:
            self._generate_hud_background()
        surface.blit(self._hud_bg_surface, self._hud_rect.topleft)
    
    def _draw_portrait(self, surface: pg.Surface) -> None:
        """Draw player portrait with border."""
        # Draw border
        border_rect = self._portrait_rect.inflate(4, 4)
        pg.draw.rect(surface, (139, 69, 19), border_rect, border_radius=4)
        
        # Draw portrait
        surface.blit(self._portrait, self._portrait_rect)
    
    def _draw_health(self, surface: pg.Surface, player: Player) -> None:
        """Draw health hearts."""
        # Draw background for hearts
        hearts_bg_rect = self._hearts_rect.inflate(20, 10)
        hearts_bg_rect.x -= 10
        hearts_bg_rect.y -= 5
        pg.draw.rect(surface, (80, 0, 0, 150), hearts_bg_rect, border_radius=4)
        
        # Calculate hearts to display
        hearts_to_show = int(player.health_percentage * PlayerConstants.MAX_HEARTS_DISPLAY)
        
        # Draw hearts
        for i in range(PlayerConstants.MAX_HEARTS_DISPLAY):
            heart_x = self._hearts_rect.x + i * (UIConstants.HEART_SIZE[0] + 2)
            heart_y = self._hearts_rect.y
            
            if i < hearts_to_show:
                surface.blit(self._heart_full, (heart_x, heart_y))
            else:
                surface.blit(self._heart_empty, (heart_x, heart_y))
    
    def _draw_coins(self, surface: pg.Surface, player: Player) -> None:
        """Draw coin counter."""
        # Draw background
        pg.draw.rect(surface, (139, 69, 19, 200), self._coin_rect, border_radius=4)
        
        # Draw coin icon
        coin_pos = (self._coin_rect.x + 5, self._coin_rect.y + 3)
        surface.blit(self._coin_icon, coin_pos)
        
        # Draw coin count
        coin_text = self._font.render(str(player.coins), True, (255, 215, 0))
        text_pos = (coin_pos[0] + UIConstants.ICON_SIZE[0] + 10, coin_pos[1] + 2)
        surface.blit(coin_text, text_pos)
    
    def _draw_mana(self, surface: pg.Surface, player: Player) -> None:
        """Draw mana bar."""
        # Draw background (empty bar)
        pg.draw.rect(surface, (30, 30, 80), self._mana_bar_rect, border_radius=4)
        
        # Draw filled portion
        if player.max_mana > 0:
            fill_width = int(self._mana_bar_rect.width * player.mana_percentage)
            if fill_width > 0:
                fill_rect = pg.Rect(
                    self._mana_bar_rect.x,
                    self._mana_bar_rect.y,
                    fill_width,
                    self._mana_bar_rect.height
                )
                pg.draw.rect(surface, (30, 30, 200), fill_rect, border_radius=4)
        
        # Draw mana text
        mana_text = self._font.render(
            f"{player.mana}/{player.max_mana}",
            True,
            (200, 200, 255)
        )
        text_rect = mana_text.get_rect(center=self._mana_bar_rect.center)
        surface.blit(mana_text, text_rect)