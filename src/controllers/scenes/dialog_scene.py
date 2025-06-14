"""Dialog scene controller for standalone story sequences."""
from __future__ import annotations

from typing import Optional
from pathlib import Path
import pygame as pg

from src.controllers.base.scene import BaseScene
from src.views.renderers.dialog_renderer import DialogRenderer
from src.models.ui.dialog import get_dialog_manager, DialogSequence
from src.models.config import Config
from src.core.constants import AssetPaths
from src.core.exceptions import DialogError


class DialogScene(BaseScene):
    """Standalone dialog scene for story sequences."""
    
    def __init__(
        self,
        config: Config,
        dialog_id: str,
        next_scene: str = "game"
    ) -> None:
        """
        Initialize dialog scene.
        
        Args:
            config: Game configuration
            dialog_id: ID of dialog sequence to play
            next_scene: Scene to transition to after dialog
        """
        super().__init__(config)
        
        # Create renderer
        self._renderer = DialogRenderer()
        
        # Dialog state
        self._dialog_id = dialog_id
        self._next_scene_id = next_scene
        self._sequence: Optional[DialogSequence] = None
        
        # Load dialog sequence
        self._load_dialog()
    
    def handle_events(self) -> Optional[str]:
        """Process dialog input events."""
        for event in pg.event.get():
            # Handle common events
            action = self._handle_common_events(event)
            if action:
                return action
            
            # Let renderer handle dialog events
            if self._renderer.handle_event(event):
                # Check if dialog finished
                if self._renderer.is_finished():
                    return self._next_scene_id
        
        return None
    
    def update(self, delta_time: float) -> None:
        """Update dialog state."""
        # Dialog updates are handled by renderer
        pass
    
    def render(self) -> None:
        """Render dialog scene."""
        self._renderer.render(self.screen)
    
    def on_enter(self) -> None:
        """Called when entering dialog scene."""
        super().on_enter()
        
        # Update screen reference
        self._renderer.update_screen_size(self.screen.get_width(), self.screen.get_height())
        
        # Stop any playing music
        pg.mixer.music.stop()
    
    def on_exit(self) -> None:
        """Called when exiting dialog scene."""
        super().on_exit()
        
        # Stop any playing sounds
        pg.mixer.stop()
    
    def _load_dialog(self) -> None:
        """Load dialog sequence from file."""
        dialog_manager = get_dialog_manager()
        
        # Try to load from standard location
        dialog_path = Path(AssetPaths.GAME_DIALOGS) / f"{self._dialog_id}.json"
        
        try:
            self._sequence = dialog_manager.load_sequence_from_file(
                self._dialog_id,
                dialog_path
            )
            self._renderer.set_sequence(self._sequence)
        except DialogError as e:
            print(f"Failed to load dialog {self._dialog_id}: {e}")
            # Create empty sequence to avoid crashes
            from src.models.ui.dialog import DialogEntry, DialogSequence
            self._sequence = DialogSequence([
                DialogEntry(text="[Dialog not found]")
            ])
            self._renderer.set_sequence(self._sequence)