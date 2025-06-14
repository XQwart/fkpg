"""Menu renderer with background and music management."""
from __future__ import annotations

from typing import List, Tuple, Optional
from pathlib import Path
import random
import pygame as pg

from src.core.constants import UIConstants, AssetPaths
from src.core.interfaces import IRenderer
from src.core.exceptions import ResourceError


# Menu assets
# Menu assets
# Backgrounds used in a slideshow behind the menu
MENU_BACKGROUNDS = [
    "background_1.png",
    "background_2.png",
    "background_3.png",
]

# Music tracks that play while user is in the menu
MENU_MUSIC_TRACKS = [
    "menu_soundtrack_1.mp3",
    "menu_soundtrack_2.mp3",
    "menu_soundtrack_3.mp3",
]


class MenuItem:
    """Single menu item with text, associated image and state."""
    
    def __init__(self, text: str, action: str, enabled: bool = True):
        """Initialize menu item.

        Parameters
        ----------
        text : str
            Fallback caption for the button (used if image is missing).
        action : str
            Action identifier returned when the button is clicked.
        enabled : bool, optional
            Whether the button is clickable, by default True
        """
        self.text = text
        self.action = action
        self.enabled = enabled
        self.rect = pg.Rect(0, 0, 0, 0)
        # Image surface for the normal state. May be None if image not found.
        self.image: Optional[pg.Surface] = None


# Mapping of menu actions to button image filenames (relative to AssetPaths.MENU_IMAGES)
# Scale factor for button images (0 < SCALE <= 1)
BUTTON_IMAGE_SCALE = 0.5

# Added mapping for locked continue button version
MENU_BUTTON_IMAGES = {
    "continue": "continue_buttton.png",      # original enabled continue button
    "continue_locked": "continue_locked_buttton.png",  # disabled continue button
    "new_game": "new_game_button.png",
    "settings": "settings_button.png",
    "exit": "exit_button.png",
}


class MenuRenderer(IRenderer):
    """Renders main menu with animated backgrounds."""
    
    # Custom event for music end
    MUSIC_END_EVENT = pg.USEREVENT + 1
    
    def __init__(self) -> None:
        """Initialize menu renderer."""
        self._screen_size = (800, 600)
        self._font: Optional[pg.font.Font] = None

        # Hover/click sounds and hover tracking
        self._hover_sound: Optional[pg.mixer.Sound] = None
        self._click_sound: Optional[pg.mixer.Sound] = None
        self._last_hovered_item: Optional[MenuItem] = None
        
        # Background management
        self._backgrounds: List[pg.Surface] = []
        self._current_bg_index = 0
        self._current_bg: Optional[pg.Surface] = None
        self._next_bg: Optional[pg.Surface] = None
        
        # Fade transition
        self._fade_active = False
        self._fade_start_time = 0
        self._fade_duration = UIConstants.MENU_FADE_DURATION_MS
        self._next_bg_index = 0
        
        # Menu items
        self._items: List[MenuItem] = []
        
        # Initialize assets
        self._button_images: dict[str, pg.Surface] = {}
        self._load_assets()
    
    def set_menu_items(self, items: List[MenuItem]) -> None:
        """Set menu items to display (assigning images automatically)."""
        self._items = items

        # Attach pre-loaded images to corresponding items when available
        for item in self._items:
            if item.action in self._button_images:
                item.image = self._button_images[item.action]

        self._layout_items()
    
    def play_click_sound(self) -> None:
        """Play click sound effect."""
        if self._click_sound:
            self._click_sound.play()

    def get_item_at_position(self, pos: Tuple[int, int]) -> Optional[MenuItem]:
        """Get menu item at mouse position."""
        for item in self._items:
            if item.enabled and item.rect.collidepoint(pos):
                return item
        return None
    
    def start_background_transition(self) -> None:
        """Start transition to next background."""
        if self._fade_active or len(self._backgrounds) <= 1:
            return
        
        # Choose next background (different from current)
        self._next_bg_index = (self._current_bg_index + random.randint(1, len(self._backgrounds) - 1)) % len(self._backgrounds)
        self._next_bg = self._backgrounds[self._next_bg_index].copy()
        self._next_bg.set_alpha(0)
        
        self._fade_active = True
        self._fade_start_time = pg.time.get_ticks()
        
        # Play next music track
        self._play_music(self._next_bg_index)
    
    def render(self, surface: pg.Surface) -> None:
        """Render menu to surface."""
        # Update screen size if changed
        if surface.get_size() != self._screen_size:
            self.update_screen_size(surface.get_width(), surface.get_height())
        
        # Update fade transition
        if self._fade_active:
            self._update_fade()
        
        # Draw current background
        if self._current_bg:
            surface.blit(self._current_bg, (0, 0))
        
        # Draw fade transition
        if self._fade_active and self._next_bg:
            surface.blit(self._next_bg, (0, 0))
        
        # Draw menu items
        self._render_menu_items(surface)
    
    def update_screen_size(self, width: int, height: int) -> None:
        """Update renderer for new screen dimensions."""
        self._screen_size = (width, height)
        
        # Rescale backgrounds
        self._rescale_backgrounds()
        
        # Re-layout menu items
        self._layout_items()
    
    def _load_assets(self) -> None:
        """Load menu assets (backgrounds, music, button images)."""
        # Initialize font (used as fallback if button image missing)
        self._font = pg.font.Font(None, UIConstants.FONT_SIZE_LARGE)

        # ------------- Load button images -------------
        btn_path_root = Path(AssetPaths.MENU_IMAGES)
        for action, filename in MENU_BUTTON_IMAGES.items():
            img_path = btn_path_root / filename
            try:
                if img_path.exists():
                    image = pg.image.load(str(img_path)).convert_alpha()
                    # Scale down the image to make buttons smaller
                    if 0 < BUTTON_IMAGE_SCALE < 1.0:
                        w, h = image.get_size()
                        new_size = (int(w * BUTTON_IMAGE_SCALE), int(h * BUTTON_IMAGE_SCALE))
                        image = pg.transform.smoothscale(image, new_size)
                    self._button_images[action] = image
            except pg.error:
                # Ignore loading errors (missing/corrupt assets)
                pass
        
        # ------------- Load sounds -------------
        snd_path_root = Path(AssetPaths.MENU_SOUNDS)
        try:
            hover_path = snd_path_root / "hover_button.mp3"
            click_path = snd_path_root / "clik_button.mp3"
            if hover_path.exists():
                self._hover_sound = pg.mixer.Sound(str(hover_path))
            if click_path.exists():
                self._click_sound = pg.mixer.Sound(str(click_path))
        except pg.error:
            # Ignore missing/invalid sound files
            pass

        # ------------- Load backgrounds -------------
        menu_path = Path(AssetPaths.MENU_IMAGES)
        for bg_file in MENU_BACKGROUNDS:
            try:
                bg_path = menu_path / bg_file
                if bg_path.exists():
                    bg = pg.image.load(str(bg_path)).convert()
                    self._backgrounds.append(bg)
            except pg.error:
                pass
        
        # Ensure at least one background
        if not self._backgrounds:
            # Create gradient background as fallback
            fallback = pg.Surface(self._screen_size)
            for y in range(self._screen_size[1]):
                color_value = int(50 + (y / self._screen_size[1]) * 50)
                pg.draw.line(fallback, (color_value, 0, color_value), (0, y), (self._screen_size[0], y))
            self._backgrounds.append(fallback)
        
        # Set initial background
        self._current_bg_index = random.randrange(len(self._backgrounds))
        self._rescale_backgrounds()
        
        # Start initial music
        self._play_music(self._current_bg_index)
    
    def _rescale_backgrounds(self) -> None:
        """Rescale all backgrounds to current screen size."""
        scaled_bgs = []
        
        for original_bg in self._backgrounds:
            scaled = pg.transform.scale(original_bg, self._screen_size)
            scaled_bgs.append(scaled)
        
        # Update current background
        if self._current_bg_index < len(scaled_bgs):
            self._current_bg = scaled_bgs[self._current_bg_index]
        
        # Update fade transition if active
        if self._fade_active and self._next_bg_index < len(scaled_bgs):
            alpha = self._next_bg.get_alpha() if self._next_bg else 0
            self._next_bg = scaled_bgs[self._next_bg_index].copy()
            self._next_bg.set_alpha(alpha)
    
    def _layout_items(self) -> None:
        """Calculate menu item positions."""
        if not self._items or not self._font:
            return
        
        # Calculate total height based on images (fallback to font height)
        heights = []
        for itm in self._items:
            if itm.image is not None:
                heights.append(itm.image.get_height())
            else:
                heights.append(self._font.get_height())
        total_height = sum(heights) + (len(self._items) - 1) * UIConstants.MENU_ITEM_SPACING
        
        # Start position (centered vertically)
        y = (self._screen_size[1] - total_height) // 2
        center_x = self._screen_size[0] // 2
        
        # Position each item
        for idx, item in enumerate(self._items):
            if item.image is not None:
                w, h = item.image.get_size()
            else:
                w, h = self._font.size(item.text)

            item.rect = pg.Rect(0, 0, w, h)
            item.rect.midtop = (center_x, y)
            y += h + UIConstants.MENU_ITEM_SPACING
    
    def _render_menu_items(self, surface: pg.Surface) -> None:
        """Render menu items with hover effects (image buttons preferred)."""
        if not self._font:
            return

        mouse_pos = pg.mouse.get_pos()
        hovered_item: Optional[MenuItem] = None

        for item in self._items:
            # Base button image
            button_image: Optional[pg.Surface] = item.image

            if button_image is not None:
                # Use image button rendering
                button_surf = button_image.copy()

                # Apply visual state cues
                if not item.enabled:
                    # Gray-out disabled button
                    gray_overlay = pg.Surface(button_surf.get_size(), pg.SRCALPHA)
                    gray_overlay.fill((100, 100, 100, 255))
                    button_surf.blit(gray_overlay, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
                    button_surf.set_alpha(240)
                elif item.rect.collidepoint(mouse_pos):
                    button_surf.set_alpha(255)
                    hovered_item = item
                else:
                    button_surf.set_alpha(220)

                surface.blit(button_surf, item.rect)
            else:
                # Fallback to simple text rendering
                if not item.enabled:
                    color = (120, 120, 120)
                elif item.rect.collidepoint(mouse_pos):
                    color = (255, 255, 255)
                    hovered_item = item
                else:
                    color = (200, 200, 200)

                text_surface = self._font.render(item.text, True, color)
                surface.blit(text_surface, item.rect)

        # Play hover sound on item change
        if hovered_item is not None and hovered_item != self._last_hovered_item:
            if self._hover_sound:
                self._hover_sound.play()
        self._last_hovered_item = hovered_item
    
    def _update_fade(self) -> None:
        """Update background fade transition."""
        if not self._fade_active or not self._next_bg:
            return
        
        # Calculate fade progress
        elapsed = pg.time.get_ticks() - self._fade_start_time
        progress = min(1.0, elapsed / self._fade_duration)
        alpha = int(255 * progress)
        
        self._next_bg.set_alpha(alpha)
        
        # Check if fade complete
        if progress >= 1.0:
            self._current_bg_index = self._next_bg_index
            self._current_bg = self._backgrounds[self._current_bg_index]
            self._fade_active = False
            self._next_bg = None
    
    def _play_music(self, index: int) -> None:
        """Play menu music track."""
        if index >= len(MENU_MUSIC_TRACKS):
            return
        
        music_path = Path(AssetPaths.MENU_SOUNDS) / MENU_MUSIC_TRACKS[index]
        
        try:
            if music_path.exists():
                pg.mixer.music.load(str(music_path))
                pg.mixer.music.play()
                pg.mixer.music.set_endevent(self.MUSIC_END_EVENT)
        except pg.error:
            pass  # Silently ignore music errors