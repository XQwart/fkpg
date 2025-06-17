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
        self._fade_progress = 0.0
        self._fade_target = 1.0
        self._fade_speed = 0.02
        self._last_update_time = 0
        
    def set_sequence(self, sequence: DialogSequence) -> None:
        """Set dialog sequence to render."""
        self._overlay.set_sequence(sequence)
        # Always show for standalone renderer
        self._overlay.show()
        self._fade_progress = 0.0
        self._fade_target = 1.0
    
    def handle_event(self, event: pg.event.Event) -> bool:
        """Handle input event."""
        return self._overlay.handle_event(event)
    
    def render(self, surface: pg.Surface) -> None:
        """Render dialog scene."""
        # Update fade animation
        current_time = pg.time.get_ticks()
        if self._last_update_time > 0:
            delta_time = (current_time - self._last_update_time) / 1000.0
            
            if self._fade_progress < self._fade_target:
                self._fade_progress = min(self._fade_target,
                                        self._fade_progress + self._fade_speed * delta_time * 60)
            elif self._fade_progress > self._fade_target:
                self._fade_progress = max(self._fade_target,
                                        self._fade_progress - self._fade_speed * delta_time * 60)
        
        self._last_update_time = current_time
        
        # Create gradient background
        self._draw_gradient_background(surface)
        
        # Apply fade effect to background
        if self._fade_progress < 1.0:
            fade_surface = pg.Surface(surface.get_size())
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(int((1.0 - self._fade_progress) * 255))
            surface.blit(fade_surface, (0, 0))
        
        # Render dialog
        self._overlay.render(surface)
    
    def update_screen_size(self, width: int, height: int) -> None:
        """Update renderer for new screen dimensions."""
        self._overlay.update_screen_size(width, height)
    
    def is_finished(self) -> bool:
        """Check if dialog sequence has finished."""
        sequence = self._overlay._sequence
        return sequence is None or sequence.is_finished
    
    def _draw_gradient_background(self, surface: pg.Surface) -> None:
        """Draw a beautiful gradient background."""
        width, height = surface.get_size()
        
        # Create vertical gradient from dark blue to black
        for y in range(height):
            progress = y / height
            # Interpolate between dark blue and black
            r = int(10 * (1 - progress))
            g = int(10 * (1 - progress))
            b = int(30 * (1 - progress))
            
            color = (r, g, b)
            pg.draw.line(surface, color, (0, y), (width, y))
        
        # Add some ambient particles/stars for atmosphere
        if not hasattr(self, '_star_positions'):
            import random
            self._star_positions = []
            for _ in range(50):
                x = random.randint(0, width)
                y = random.randint(0, height)
                brightness = random.randint(50, 200)
                size = random.choice([1, 1, 1, 2])  # Most stars are small
                twinkle_speed = random.uniform(0.5, 2.0)
                self._star_positions.append((x, y, brightness, size, twinkle_speed))
        
        # Draw twinkling stars
        import math
        time = pg.time.get_ticks() / 1000.0
        for x, y, max_brightness, size, speed in self._star_positions:
            # Calculate twinkle effect
            brightness = int(max_brightness * (0.5 + 0.5 * math.sin(time * speed)))
            color = (brightness, brightness, min(255, brightness + 50))
            
            if size == 1:
                surface.set_at((x, y), color)
            else:
                pg.draw.circle(surface, color, (x, y), size)
                # Add glow for larger stars
                if size > 1:
                    glow_surface = pg.Surface((size * 6, size * 6), pg.SRCALPHA)
                    pg.draw.circle(glow_surface, (*color[:2], color[2], 30), 
                                 (size * 3, size * 3), size * 3)
                    surface.blit(glow_surface, (x - size * 3, y - size * 3))