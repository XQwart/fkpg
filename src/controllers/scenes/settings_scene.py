"""Settings scene controller."""
from __future__ import annotations

from typing import Optional
import pygame as pg

from src.controllers.base.scene import BaseScene
from src.views.renderers.settings_renderer import SettingsRenderer, SettingItem, SettingType
from src.models.config import Config
from src.core.constants import ALLOWED_FPS_VALUES, VOLUME_STEP


class SettingsScene(BaseScene):
    """Settings menu scene for configuring game options."""
    
    def __init__(self, config: Config) -> None:
        """Initialize settings scene."""
        super().__init__(config)
        
        # Create renderer
        self._renderer = SettingsRenderer()
        
        # Create setting items
        self._create_setting_items()
        
        # State
        self._waiting_for_key = False
    
    def handle_events(self) -> Optional[str]:
        """Process settings input events."""
        for event in pg.event.get():
            # Handle common events
            action = self._handle_common_events(event)
            if action:
                return action
            
            # Handle settings-specific events
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    if self._renderer.is_waiting_for_key():
                        # Cancel key binding
                        self._renderer.set_waiting_for_key(None)
                    else:
                        # Return to menu
                        return "menu"
                
                elif self._renderer.is_waiting_for_key():
                    # Apply new key binding
                    identifier = self._renderer.get_waiting_identifier()
                    if identifier:
                        self._apply_key_binding(identifier, event.key)
                        self._renderer.set_waiting_for_key(None)
            
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if not self._renderer.is_waiting_for_key():
                    # Check setting item clicks
                    item = self._renderer.get_item_at_position(event.pos)
                    if item:
                        self._handle_item_click(item)
        
        return None
    
    def update(self, delta_time: float) -> None:
        """Update settings state."""
        # Update item values from config
        self._update_item_values()
    
    def render(self) -> None:
        """Render settings scene."""
        self._renderer.render(self.screen)
    
    def on_enter(self) -> None:
        """Called when entering settings scene."""
        super().on_enter()
        
        # Update screen reference
        self._renderer.update_screen_size(self.screen.get_width(), self.screen.get_height())
        
        # Update item values
        self._update_item_values()
    
    def on_exit(self) -> None:
        """Called when exiting settings scene."""
        super().on_exit()
        
        # Save configuration
        self.config.save()
    
    def _create_setting_items(self) -> None:
        """Create setting items."""
        items = [
            # Key bindings
            SettingItem("Move Left", "left", SettingType.KEY_BINDING),
            SettingItem("Move Right", "right", SettingType.KEY_BINDING),
            SettingItem("Jump", "jump", SettingType.KEY_BINDING),
            SettingItem("Sprint", "sprint", SettingType.KEY_BINDING),
            SettingItem("Block", "block", SettingType.KEY_BINDING),
            
            # Display settings
            SettingItem("VSync", "vsync", SettingType.TOGGLE),
            SettingItem("FPS Limit", "fps", SettingType.SLIDER),
            
            # Audio settings
            SettingItem("Music Volume", "volume", SettingType.SLIDER),
            
            # Actions
            SettingItem("Back", "back", SettingType.ACTION),
        ]
        
        self._renderer.set_items(items)
        self._update_item_values()
    
    def _update_item_values(self) -> None:
        """Update item values from configuration."""
        for item in self._renderer._items:
            if item.setting_type == SettingType.KEY_BINDING:
                # Get key binding value
                item.value = getattr(self.config.key_bindings, item.identifier, 0)
            
            elif item.identifier == "vsync":
                item.value = self.config.display.vsync
            
            elif item.identifier == "fps":
                item.value = self.config.display.fps_limit
            
            elif item.identifier == "volume":
                item.value = self.config.audio.music_volume
    
    def _handle_item_click(self, item: SettingItem) -> None:
        """Handle click on setting item."""
        if item.setting_type == SettingType.KEY_BINDING:
            # Start waiting for key
            self._renderer.set_waiting_for_key(item.identifier)
        
        elif item.setting_type == SettingType.TOGGLE:
            if item.identifier == "vsync":
                self.config.toggle_vsync()
        
        elif item.setting_type == SettingType.SLIDER:
            if item.identifier == "fps" and not self.config.display.vsync:
                self.config.cycle_fps_limit()
            elif item.identifier == "volume":
                # Cycle volume in steps
                new_volume = self.config.audio.music_volume + VOLUME_STEP
                if new_volume > 1.0:
                    new_volume = 0.0
                self.config.set_music_volume(new_volume)
        
        elif item.setting_type == SettingType.ACTION:
            if item.identifier == "back":
                self.transition_to("menu")
    
    def _apply_key_binding(self, identifier: str, key: int) -> None:
        """Apply new key binding."""
        self.config.update_key_binding(identifier, key)