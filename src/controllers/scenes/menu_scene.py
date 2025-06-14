"""Main menu scene controller."""
from __future__ import annotations

from typing import Optional
from pathlib import Path
import pygame as pg

from src.controllers.base.scene import BaseScene
from src.views.renderers.menu_renderer import MenuRenderer, MenuItem
from src.models.config import Config
from src.core.constants import SAVE_FILE


class MenuScene(BaseScene):
    """Main menu scene with background and music."""
    
    def __init__(self, config: Config) -> None:
        """Initialize menu scene."""
        super().__init__(config)
        
        # Create renderer
        self._renderer = MenuRenderer()
        
        # Create menu items
        self._create_menu_items()
        
        # State
        self._music_volume_applied = False
    
    def handle_events(self) -> Optional[str]:
        """Process menu input events."""
        for event in pg.event.get():
            # Handle common events
            action = self._handle_common_events(event)
            if action:
                return action
            
            # Handle menu-specific events
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    return "exit"
            
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                # Check menu item clicks
                item = self._renderer.get_item_at_position(event.pos)
                if item and item.enabled:
                    return item.action
            
            elif event.type == MenuRenderer.MUSIC_END_EVENT:
                # Start background transition when music ends
                self._renderer.start_background_transition()
        
        return None
    
    def update(self, delta_time: float) -> None:
        """Update menu state."""
        # Apply music volume if not already done
        if not self._music_volume_applied:
            pg.mixer.music.set_volume(self.config.audio.music_volume)
            self._music_volume_applied = True
    
    def render(self) -> None:
        """Render menu scene."""
        self._renderer.render(self.screen)
    
    def on_enter(self) -> None:
        """Called when entering menu scene."""
        super().on_enter()
        
        # Update screen reference
        self._renderer.update_screen_size(self.screen.get_width(), self.screen.get_height())
        
        # Check if save file exists and update Continue button
        self._update_continue_availability()
    
    def on_exit(self) -> None:
        """Called when exiting menu scene."""
        super().on_exit()
    
    def _create_menu_items(self) -> None:
        """Create menu items."""
        items = [
            MenuItem("CONTINUE", "continue", enabled=False),
            MenuItem("NEW GAME", "new_game", enabled=True),
            MenuItem("SETTINGS", "settings", enabled=True),
            MenuItem("EXIT", "exit", enabled=True),
        ]
        
        self._renderer.set_menu_items(items)
    
    def _update_continue_availability(self) -> None:
        """Check if continue should be enabled."""
        save_path = Path(SAVE_FILE)
        can_continue = save_path.exists()
        
        # Update continue button state
        items = self._renderer._items
        for item in items:
            if item.action == "continue":
                item.enabled = can_continue
                break