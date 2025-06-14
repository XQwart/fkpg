"""Dialog renderer for both standalone scenes and overlays."""
from __future__ import annotations

from typing import Optional
import pygame as pg

from src.views.ui.dialog_overlay import DialogOverlay
from src.models.ui.dialog import DialogSequence
from src.core.interfaces import IRenderer


class DialogRenderer(IRenderer):
    """Renders dialog sequences as full-screen scenes."""
    
    def __init__(self) -> None:
        """Initialize dialog renderer."""
        # Reuse dialog overlay for rendering
        self._overlay = DialogOverlay()
        self._background_color = (0, 0, 0)
        
    def set_sequence(self, sequence: DialogSequence) -> None:
        """Set dialog sequence to render."""
        self._overlay.set_sequence(sequence)
        # Always show for standalone renderer
        self._overlay.show()
    
    def handle_event(self, event: pg.event.Event) -> bool:
        """Handle input event."""
        return self._overlay.handle_event(event)
    
    def render(self, surface: pg.Surface) -> None:
        """Render dialog scene."""
        # Fill background
        surface.fill(self._background_color)
        
        # Render dialog
        self._overlay.render(surface)
    
    def update_screen_size(self, width: int, height: int) -> None:
        """Update renderer for new screen dimensions."""
        self._overlay.update_screen_size(width, height)
    
    def is_finished(self) -> bool:
        """Check if dialog sequence has finished."""
        sequence = self._overlay._sequence
        return sequence is None or sequence.is_finished