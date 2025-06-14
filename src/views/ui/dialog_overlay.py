"""Dialog overlay view for in-game conversations."""
from __future__ import annotations

from typing import Optional
from pathlib import Path
import pygame as pg

from src.models.ui.dialog import DialogSequence, DialogEntry
from src.core.constants import UIConstants, AssetPaths, DIALOG_PADDING, DIALOG_TEXT_BOX_HEIGHT_RATIO
from src.core.interfaces import IOverlay
from src.core.exceptions import ResourceError


class DialogOverlay(IOverlay):
    """Overlay for displaying dialog during gameplay."""
    
    def __init__(self) -> None:
        """Initialize dialog overlay."""
        self._visible = False
        self._sequence: Optional[DialogSequence] = None
        self._font: Optional[pg.font.Font] = None
        self._name_font: Optional[pg.font.Font] = None
        self._screen_size = (800, 600)  # Default size
        
        # Pre-rendered surfaces
        self._text_background: Optional[pg.Surface] = None
        self._name_background: Optional[pg.Surface] = None
        self._default_portrait: Optional[pg.Surface] = None
        self._dimmer: Optional[pg.Surface] = None
        
        # Layout rectangles
        self._text_box_rect = pg.Rect(0, 0, 100, 100)
        self._name_box_rect = pg.Rect(0, 0, UIConstants.NAME_BOX_WIDTH, UIConstants.NAME_BOX_HEIGHT)
        self._portrait_rect = pg.Rect(0, 0, *UIConstants.PORTRAIT_SIZE_DIALOG)
        
        # Sound management
        self._current_sound: Optional[pg.mixer.Sound] = None
        self._current_sound_channel: Optional[pg.mixer.Channel] = None
        
        self._initialize_assets()
    
    def show(self) -> None:
        """Show the dialog overlay."""
        self._visible = True
    
    def hide(self) -> None:
        """Hide the dialog overlay."""
        self._visible = False
        self._stop_current_sound()
    
    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        return self._visible
    
    def set_sequence(self, sequence: DialogSequence) -> None:
        """Set dialog sequence to display."""
        self._sequence = sequence
        if sequence:
            self.show()
            # Play sound for first entry if available
            entry = sequence.current_entry
            if entry.sound:
                self._play_sound(entry.sound)
    
    def handle_event(self, event: pg.event.Event) -> bool:
        """
        Handle input event.
        
        Returns:
            True if event was consumed by overlay
        """
        if not self._visible or not self._sequence:
            return False
        
        # Handle dialog advancement
        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_SPACE, pg.K_RETURN):
                self._advance_dialog()
                return True
            elif event.key == pg.K_ESCAPE:
                # Skip to end
                self._sequence.skip_to_end()
                self._advance_dialog()
                return True
        
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self._advance_dialog()
            return True
        
        # Consume all events when dialog is showing
        return True
    
    def render(self, surface: pg.Surface) -> None:
        """Render dialog overlay to surface."""
        if not self._visible or not self._sequence:
            return
        
        # Update screen size if changed
        if surface.get_size() != self._screen_size:
            self._screen_size = surface.get_size()
            self._update_layout()
        
        # Get current dialog entry
        entry = self._sequence.current_entry
        
        # Apply screen dimmer
        surface.blit(self._dimmer, (0, 0))
        
        # Draw dialog background image if specified
        if entry.image:
            self._draw_background_image(surface, entry.image)
        
        # Draw text box background
        surface.blit(self._text_background, self._text_box_rect)
        
        # Draw name box
        self._draw_name_box(surface, entry.speaker)
        
        # Draw portrait
        self._draw_portrait(surface, entry.portrait)
        
        # Draw dialog text
        self._draw_dialog_text(surface, entry.text)
        
        # Draw scroll indicator
        if not self._sequence.is_finished:
            self._draw_scroll_indicator(surface)
    
    def update_screen_size(self, width: int, height: int) -> None:
        """Update overlay for new screen dimensions."""
        self._screen_size = (width, height)
        self._update_layout()
    
    def _initialize_assets(self) -> None:
        """Initialize fonts and default assets."""
        # Initialize fonts
        self._font = pg.font.Font(None, UIConstants.FONT_SIZE_SMALL)
        self._name_font = pg.font.Font(None, 32)
        
        # Create default portrait
        self._create_default_portrait()
    
    def _update_layout(self) -> None:
        """Update layout based on screen size."""
        width, height = self._screen_size
        
        # Calculate text box dimensions
        text_box_height = int(height * DIALOG_TEXT_BOX_HEIGHT_RATIO)
        self._text_box_rect = pg.Rect(
            DIALOG_PADDING,
            height - text_box_height - DIALOG_PADDING,
            width - 2 * DIALOG_PADDING,
            text_box_height
        )
        
        # Update backgrounds
        self._create_text_background()
        self._create_name_background()
        
        # Update dimmer
        self._dimmer = pg.Surface(self._screen_size, pg.SRCALPHA)
        self._dimmer.fill((0, 0, 0, 100))
        
        # Update portrait position
        self._portrait_rect.topleft = (
            DIALOG_PADDING + 20,
            self._text_box_rect.y - UIConstants.PORTRAIT_SIZE_DIALOG[1] // 2
        )
        
        # Update name box position
        self._name_box_rect.topleft = (
            DIALOG_PADDING + 200,
            self._text_box_rect.y - 60
        )
    
    def _create_text_background(self) -> None:
        """Create semi-transparent background for text box."""
        self._text_background = pg.Surface(self._text_box_rect.size, pg.SRCALPHA)
        pg.draw.rect(
            self._text_background,
            (0, 0, 0, 180),
            self._text_background.get_rect(),
            border_radius=15
        )
    
    def _create_name_background(self) -> None:
        """Create background for speaker name box."""
        self._name_background = pg.Surface(self._name_box_rect.size, pg.SRCALPHA)
        pg.draw.rect(
            self._name_background,
            (20, 20, 20, 200),
            self._name_background.get_rect(),
            border_radius=10
        )
    
    def _create_default_portrait(self) -> None:
        """Create default portrait for speakers without custom portraits."""
        self._default_portrait = pg.Surface(UIConstants.PORTRAIT_SIZE_DIALOG, pg.SRCALPHA)
        
        # Background
        pg.draw.rect(
            self._default_portrait,
            (50, 50, 80),
            (0, 0, *UIConstants.PORTRAIT_SIZE_DIALOG),
            border_radius=10
        )
        
        # Silhouette
        head_center = (
            UIConstants.PORTRAIT_SIZE_DIALOG[0] // 2,
            UIConstants.PORTRAIT_SIZE_DIALOG[1] // 3
        )
        head_radius = min(UIConstants.PORTRAIT_SIZE_DIALOG) // 4
        pg.draw.circle(self._default_portrait, (150, 150, 170), head_center, head_radius)
        
        body_rect = pg.Rect(
            UIConstants.PORTRAIT_SIZE_DIALOG[0] // 4,
            UIConstants.PORTRAIT_SIZE_DIALOG[1] // 2,
            UIConstants.PORTRAIT_SIZE_DIALOG[0] // 2,
            UIConstants.PORTRAIT_SIZE_DIALOG[1] // 3
        )
        pg.draw.rect(self._default_portrait, (120, 120, 140), body_rect, border_radius=5)
    
    def _draw_background_image(self, surface: pg.Surface, image_path: str) -> None:
        """Draw background image for dialog."""
        try:
            image = pg.image.load(image_path).convert_alpha()
            # Scale to fit screen while maintaining aspect ratio
            image_rect = image.get_rect()
            scale = min(
                self._screen_size[0] / image_rect.width,
                self._screen_size[1] / image_rect.height
            )
            new_size = (
                int(image_rect.width * scale),
                int(image_rect.height * scale)
            )
            scaled_image = pg.transform.scale(image, new_size)
            
            # Center on screen
            pos = (
                (self._screen_size[0] - new_size[0]) // 2,
                (self._screen_size[1] - new_size[1]) // 2
            )
            surface.blit(scaled_image, pos)
            
        except (pg.error, FileNotFoundError):
            pass  # Silently ignore missing images
    
    def _draw_name_box(self, surface: pg.Surface, speaker: Optional[str]) -> None:
        """Draw speaker name box."""
        surface.blit(self._name_background, self._name_box_rect)
        
        speaker_name = speaker or "Narrator"
        name_text = self._name_font.render(speaker_name, True, (255, 255, 255))
        name_rect = name_text.get_rect(center=self._name_box_rect.center)
        surface.blit(name_text, name_rect)
    
    def _draw_portrait(self, surface: pg.Surface, portrait_path: Optional[str]) -> None:
        """Draw speaker portrait."""
        portrait = self._default_portrait
        
        if portrait_path:
            try:
                loaded_portrait = pg.image.load(portrait_path).convert_alpha()
                portrait = pg.transform.scale(loaded_portrait, UIConstants.PORTRAIT_SIZE_DIALOG)
            except (pg.error, FileNotFoundError):
                pass  # Use default portrait
        
        surface.blit(portrait, self._portrait_rect)
    
    def _draw_dialog_text(self, surface: pg.Surface, text: str) -> None:
        """Draw dialog text with word wrapping."""
        # Define text area (accounting for portrait)
        text_area = pg.Rect(
            self._portrait_rect.right + 20,
            self._text_box_rect.top + 20,
            self._text_box_rect.width - self._portrait_rect.width - 60,
            self._text_box_rect.height - 40
        )
        
        # Simple word wrapping
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if self._font.size(test_line)[0] <= text_area.width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw lines
        y = text_area.top
        line_height = self._font.get_height() + 5
        
        for line in lines:
            if y + line_height > text_area.bottom:
                break  # Text overflow
            
            text_surface = self._font.render(line, True, (255, 255, 255))
            surface.blit(text_surface, (text_area.left, y))
            y += line_height
    
    def _draw_scroll_indicator(self, surface: pg.Surface) -> None:
        """Draw indicator showing more dialog is available."""
        # Draw animated arrow at bottom of text box
        triangle_center_x = self._text_box_rect.centerx
        triangle_bottom_y = self._text_box_rect.bottom - 15
        
        triangle_points = [
            (triangle_center_x - 10, triangle_bottom_y - 15),
            (triangle_center_x + 10, triangle_bottom_y - 15),
            (triangle_center_x, triangle_bottom_y)
        ]
        
        pg.draw.polygon(surface, (200, 200, 200), triangle_points)
    
    def _advance_dialog(self) -> None:
        """Advance to next dialog entry or hide overlay."""
        if not self._sequence:
            return
        
        # Stop current sound if playing
        self._stop_current_sound()
        
        if self._sequence.is_finished:
            self.hide()
            self._sequence = None
        else:
            self._sequence.advance()
            
            # Play sound for new entry if specified
            entry = self._sequence.current_entry
            if entry.sound:
                self._play_sound(entry.sound)
    
    def _play_sound(self, sound_path: str) -> None:
        """Play dialog sound effect."""
        try:
            self._current_sound = pg.mixer.Sound(sound_path)
            self._current_sound_channel = self._current_sound.play()
        except pg.error:
            pass  # Silently ignore missing sounds
    
    def _stop_current_sound(self) -> None:
        """Stop currently playing sound if any."""
        if self._current_sound_channel and self._current_sound_channel.get_busy():
            self._current_sound_channel.stop()
        self._current_sound = None
        self._current_sound_channel = None