"""Settings menu renderer."""
from __future__ import annotations

from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import pygame as pg

from src.core.constants import UIConstants, BACKGROUND_COLOR
from src.core.interfaces import IRenderer


class SettingType(Enum):
    """Types of settings controls."""
    
    KEY_BINDING = "key"
    TOGGLE = "toggle"
    SLIDER = "slider"
    ACTION = "action"


class SettingItem:
    """Single setting item."""
    
    def __init__(
        self,
        text: str,
        identifier: str,
        setting_type: SettingType,
        value: Any = None
    ):
        """Initialize setting item."""
        self.text = text
        self.identifier = identifier
        self.setting_type = setting_type
        self.value = value
        self.rect = pg.Rect(0, 0, 0, 0)


class SettingsRenderer(IRenderer):
    """Renders settings menu interface."""
    
    def __init__(self) -> None:
        """Initialize settings renderer."""
        self._screen_size = (800, 600)
        self._font: Optional[pg.font.Font] = None
        
        # Settings items
        self._items: List[SettingItem] = []
        
        # State
        self._waiting_for_key: Optional[str] = None
        
        # Initialize
        self._initialize()
    
    def set_items(self, items: List[SettingItem]) -> None:
        """Set settings items to display."""
        self._items = items
        self._layout_items()
    
    def get_item_at_position(self, pos: Tuple[int, int]) -> Optional[SettingItem]:
        """Get setting item at mouse position."""
        for item in self._items:
            if item.rect.collidepoint(pos):
                return item
        return None
    
    def set_waiting_for_key(self, identifier: Optional[str]) -> None:
        """Set key binding waiting state."""
        self._waiting_for_key = identifier
    
    def is_waiting_for_key(self) -> bool:
        """Check if waiting for key input."""
        return self._waiting_for_key is not None
    
    def get_waiting_identifier(self) -> Optional[str]:
        """Get identifier of setting waiting for key."""
        return self._waiting_for_key
    
    def render(self, surface: pg.Surface) -> None:
        """Render settings menu."""
        # Update screen size if changed
        if surface.get_size() != self._screen_size:
            self.update_screen_size(surface.get_width(), surface.get_height())
        
        # Clear background
        surface.fill(BACKGROUND_COLOR)
        
        # Draw title
        self._draw_title(surface)
        
        # Draw settings items
        self._draw_items(surface)
        
        # Draw instructions
        self._draw_instructions(surface)
    
    def update_screen_size(self, width: int, height: int) -> None:
        """Update renderer for new screen dimensions."""
        self._screen_size = (width, height)
        self._layout_items()
    
    def format_value(self, item: SettingItem) -> str:
        """Format setting value for display."""
        if item.setting_type == SettingType.KEY_BINDING:
            if self._waiting_for_key == item.identifier:
                return "Press new key..."
            return pg.key.name(item.value).upper() if item.value else "NONE"
        
        elif item.setting_type == SettingType.TOGGLE:
            if item.identifier == "vsync":
                return "ON" if item.value else "OFF"
            return str(item.value)
        
        elif item.setting_type == SettingType.SLIDER:
            if item.identifier == "fps":
                return str(item.value) if item.value is not None else "N/A"
            elif item.identifier == "volume":
                volume = item.value if item.value is not None else 0.0
                return f"{int(volume * 100)}%"
            return str(item.value) if item.value is not None else ""
        
        return ""
    
    def _initialize(self) -> None:
        """Initialize renderer assets."""
        self._font = pg.font.Font(None, UIConstants.FONT_SIZE_MEDIUM)
    
    def _layout_items(self) -> None:
        """Calculate item positions."""
        if not self._items or not self._font:
            return
        
        # Calculate total height
        item_height = self._font.get_height()
        total_height = len(self._items) * item_height + (len(self._items) - 1) * UIConstants.SETTINGS_ITEM_SPACING
        
        # Start position (centered vertically, with offset for title)
        y = (self._screen_size[1] - total_height) // 2 + 40
        
        # Position each item
        for item in self._items:
            # Format display text
            display_text = self._get_display_text(item)
            text_width = self._font.size(display_text)[0]
            
            # Center item
            item.rect = pg.Rect(0, 0, text_width, item_height)
            item.rect.centerx = self._screen_size[0] // 2
            item.rect.top = y
            
            y += item_height + UIConstants.SETTINGS_ITEM_SPACING
    
    def _get_display_text(self, item: SettingItem) -> str:
        """Get formatted display text for item."""
        if item.setting_type == SettingType.ACTION:
            return item.text
        
        value_str = self.format_value(item)
        return f"{item.text}: {value_str}"
    
    def _draw_title(self, surface: pg.Surface) -> None:
        """Draw settings title."""
        if not self._font:
            return
            
        title_font = pg.font.Font(None, UIConstants.FONT_SIZE_LARGE)
        title_text = title_font.render("SETTINGS", True, (255, 255, 255))
        title_rect = title_text.get_rect(centerx=self._screen_size[0] // 2, top=50)
        surface.blit(title_text, title_rect)
    
    def _draw_items(self, surface: pg.Surface) -> None:
        """Draw all settings items."""
        if not self._font:
            return
        
        mouse_pos = pg.mouse.get_pos()
        
        for item in self._items:
            # Get display text
            display_text = self._get_display_text(item)
            
            # Determine color
            if item.rect.collidepoint(mouse_pos):
                if item.setting_type == SettingType.ACTION:
                    color = (180, 230, 255)
                else:
                    color = (255, 255, 255)
            else:
                color = (200, 200, 200)
            
            # Special color for waiting state
            if self._waiting_for_key == item.identifier:
                color = (255, 255, 100)
            
            # Render text
            text_surface = self._font.render(display_text, True, color)
            
            # Center text in rect
            text_rect = text_surface.get_rect(center=item.rect.center)
            surface.blit(text_surface, text_rect)
            
            # Draw slider bar for slider types
            if item.setting_type == SettingType.SLIDER and item.value is not None:
                self._draw_slider_bar(surface, item)
    
    def _draw_slider_bar(self, surface: pg.Surface, item: SettingItem) -> None:
        """Draw slider bar for slider settings."""
        # Draw below the text
        bar_width = 200
        bar_height = 8
        bar_x = item.rect.centerx - bar_width // 2
        bar_y = item.rect.bottom + 5
        
        # Background bar
        bg_rect = pg.Rect(bar_x, bar_y, bar_width, bar_height)
        pg.draw.rect(surface, (100, 100, 100), bg_rect, border_radius=4)
        
        # Filled portion
        volume = item.value if item.value is not None else 0.0
        fill_width = int(bar_width * volume) if item.identifier == "volume" else bar_width
        if fill_width > 0:
            fill_rect = pg.Rect(bar_x, bar_y, fill_width, bar_height)
            pg.draw.rect(surface, (100, 200, 255), fill_rect, border_radius=4)
        
        # Handle
        if item.identifier == "volume":
            handle_x = bar_x + int(bar_width * volume)
            handle_rect = pg.Rect(handle_x - 4, bar_y - 2, 8, bar_height + 4)
            pg.draw.rect(surface, (255, 255, 255), handle_rect, border_radius=2)
    
    def _draw_instructions(self, surface: pg.Surface) -> None:
        """Draw instruction text at bottom."""
        if not self._font:
            return
            
        instruction_font = pg.font.Font(None, 24)
        instructions = [
            "Click to modify settings",
            "ESC to return to menu"
        ]
        
        y = self._screen_size[1] - 60
        for instruction in instructions:
            text = instruction_font.render(instruction, True, (150, 150, 150))
            text_rect = text.get_rect(centerx=self._screen_size[0] // 2, top=y)
            surface.blit(text, text_rect)
            y += 25