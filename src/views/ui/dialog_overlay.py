"""Dialog overlay view for in-game conversations."""
from __future__ import annotations

from typing import Optional, List, Tuple
from pathlib import Path
import math
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
        
        # Animation states
        self._fade_alpha = 0
        self._fade_target = 255
        self._fade_speed = 10
        self._time_accumulator = 0.0
        self._last_update_time = 0
        self._arrow_animation_time = 0.0
        
        # Portrait effects
        self._portrait_scale = 0.0
        self._portrait_scale_target = 1.0
        self._portrait_scale_speed = 8.0
        
        # Text box slide animation
        self._text_box_offset = 100
        self._text_box_offset_target = 0
        self._text_box_slide_speed = 8.0
        
        # Current text cache
        self._full_text = ""
        
        self._initialize_assets()
    
    def show(self) -> None:
        """Show the dialog overlay with animation."""
        self._visible = True
        self._fade_target = 255
        self._text_box_offset = 100
        self._text_box_offset_target = 0
        self._portrait_scale = 0.0
        self._portrait_scale_target = 1.0
    
    def hide(self) -> None:
        """Hide the dialog overlay with animation."""
        self._fade_target = 0
        self._text_box_offset_target = 100
        self._portrait_scale_target = 0.0
        self._stop_current_sound()
    
    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        return self._visible or self._fade_alpha > 0
    
    def set_sequence(self, sequence: DialogSequence) -> None:
        """Set dialog sequence to display."""
        self._sequence = sequence
        if sequence:
            self.show()
            self._arrow_animation_time = 0.0
            # Play sound for first entry if available
            entry = sequence.current_entry
            if entry.sound:
                self._play_sound(entry.sound)
            self._full_text = entry.text
    
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
        if not self.is_visible() or not self._sequence:
            return
        
        # Update animations
        current_time = pg.time.get_ticks()
        if self._last_update_time > 0:
            delta_time = (current_time - self._last_update_time) / 1000.0
            self._update_animations(delta_time)
        self._last_update_time = current_time
        
        # Update screen size if changed
        if surface.get_size() != self._screen_size:
            self._screen_size = surface.get_size()
            self._update_layout()
        
        # Get current dialog entry
        entry = self._sequence.current_entry
        
        # Apply animated screen dimmer
        if self._fade_alpha > 0:
            dimmer = self._dimmer.copy()
            dimmer.set_alpha(int(self._fade_alpha * 0.4))  # 40% of fade alpha
            surface.blit(dimmer, (0, 0))
        
        # Draw dialog background image if specified
        if entry.image and self._fade_alpha > 0:
            self._draw_background_image(surface, entry.image)
        
        # Calculate animated positions
        text_box_y = self._text_box_rect.y + self._text_box_offset
        
        # Draw text box background with shadow
        if self._fade_alpha > 0:
            shadow_offset = 5
            shadow_surface = self._text_background.copy()
            shadow_surface.set_alpha(int(self._fade_alpha * 0.3))
            surface.blit(shadow_surface, (self._text_box_rect.x + shadow_offset, text_box_y + shadow_offset))
            
            text_bg = self._text_background.copy()
            text_bg.set_alpha(int(self._fade_alpha * 0.9))
            surface.blit(text_bg, (self._text_box_rect.x, text_box_y))
        
        # Draw name box with slide animation
        if entry.speaker and self._fade_alpha > 0:
            name_box_x = self._name_box_rect.x - self._text_box_offset * 0.5
            self._draw_name_box(surface, entry.speaker, name_box_x)
        
        # Draw portrait with scale animation
        if self._fade_alpha > 0 and self._portrait_scale > 0:
            self._draw_portrait(surface, entry.portrait)
        
        # Draw dialog text
        if self._fade_alpha > 0:
            self._draw_dialog_text(surface, entry.text, text_box_y)
        
        # Draw animated scroll indicator
        if not self._sequence.is_finished and self._fade_alpha > 200:
            self._draw_scroll_indicator(surface, text_box_y)
        
        # Check if fully hidden
        if self._fade_alpha <= 0 and self._fade_target == 0:
            self._visible = False
    
    def update_screen_size(self, width: int, height: int) -> None:
        """Update overlay for new screen dimensions."""
        self._screen_size = (width, height)
        self._update_layout()
    
    def _initialize_assets(self) -> None:
        """Initialize fonts and default assets."""
        # Initialize fonts with better quality
        try:
            # Try to load a custom font for better aesthetics
            self._font = pg.font.Font(None, UIConstants.FONT_SIZE_SMALL + 2)
            self._name_font = pg.font.Font(None, 36)
        except:
            self._font = pg.font.Font(None, UIConstants.FONT_SIZE_SMALL)
            self._name_font = pg.font.Font(None, 32)
        
        # Create default portrait
        self._create_default_portrait()
    
    def _update_layout(self) -> None:
        """Update layout based on screen size."""
        width, height = self._screen_size
        
        # Calculate text box dimensions with better proportions
        text_box_height = int(height * DIALOG_TEXT_BOX_HEIGHT_RATIO * 0.9)
        self._text_box_rect = pg.Rect(
            DIALOG_PADDING,
            height - text_box_height - DIALOG_PADDING,
            width - 2 * DIALOG_PADDING,
            text_box_height
        )
        
        # Update backgrounds
        self._create_text_background()
        self._create_name_background()
        
        # Update dimmer with gradient
        self._create_gradient_dimmer()
        
        # Update portrait position
        self._portrait_rect.topleft = (
            DIALOG_PADDING + 30,
            self._text_box_rect.y - UIConstants.PORTRAIT_SIZE_DIALOG[1] // 2 - 10
        )
        
        # Update name box position
        self._name_box_rect.topleft = (
            DIALOG_PADDING + 220,
            self._text_box_rect.y - 70
        )
    
    def _create_text_background(self) -> None:
        """Create beautiful gradient background for text box."""
        self._text_background = pg.Surface(self._text_box_rect.size, pg.SRCALPHA)
        
        # Create gradient background
        for i in range(self._text_box_rect.height):
            alpha = int(200 + (i / self._text_box_rect.height) * 30)
            color = (10, 10, 20, min(alpha, 230))
            pg.draw.rect(
                self._text_background,
                color,
                (0, i, self._text_box_rect.width, 1)
            )
        
        # Add border with glow effect
        border_color = (100, 150, 255, 180)
        pg.draw.rect(
            self._text_background,
            border_color,
            self._text_background.get_rect(),
            width=3,
            border_radius=20
        )
        
        # Add inner glow
        inner_rect = self._text_background.get_rect().inflate(-6, -6)
        pg.draw.rect(
            self._text_background,
            (100, 150, 255, 60),
            inner_rect,
            width=2,
            border_radius=18
        )
    
    def _create_name_background(self) -> None:
        """Create stylish background for speaker name box."""
        self._name_background = pg.Surface(self._name_box_rect.size, pg.SRCALPHA)
        
        # Main background with gradient
        for i in range(self._name_box_rect.height):
            progress = i / self._name_box_rect.height
            color = (
                int(20 + progress * 10),
                int(20 + progress * 10),
                int(40 + progress * 20),
                220
            )
            pg.draw.rect(
                self._name_background,
                color,
                (0, i, self._name_box_rect.width, 1)
            )
        
        # Decorative border
        pg.draw.rect(
            self._name_background,
            (150, 180, 255, 200),
            self._name_background.get_rect(),
            width=2,
            border_radius=15
        )
        
        # Corner accents
        accent_size = 8
        accent_color = (200, 220, 255, 255)
        # Top-left
        pg.draw.lines(self._name_background, accent_color, False,
                     [(0, accent_size), (0, 0), (accent_size, 0)], 3)
        # Top-right
        pg.draw.lines(self._name_background, accent_color, False,
                     [(self._name_box_rect.width - accent_size, 0),
                      (self._name_box_rect.width, 0),
                      (self._name_box_rect.width, accent_size)], 3)
    
    def _create_gradient_dimmer(self) -> None:
        """Create gradient dimmer for background."""
        self._dimmer = pg.Surface(self._screen_size, pg.SRCALPHA)
        
        # Create radial gradient effect
        center_x, center_y = self._screen_size[0] // 2, self._screen_size[1] // 2
        max_radius = max(self._screen_size) * 0.8
        
        for y in range(0, self._screen_size[1], 4):
            for x in range(0, self._screen_size[0], 4):
                distance = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                alpha = min(255, int(100 + (distance / max_radius) * 155))
                pg.draw.rect(self._dimmer, (0, 0, 0, alpha), (x, y, 4, 4))
    
    def _create_default_portrait(self) -> None:
        """Create stylish default portrait for speakers without custom portraits."""
        self._default_portrait = pg.Surface(UIConstants.PORTRAIT_SIZE_DIALOG, pg.SRCALPHA)
        
        # Gradient background
        for i in range(UIConstants.PORTRAIT_SIZE_DIALOG[1]):
            progress = i / UIConstants.PORTRAIT_SIZE_DIALOG[1]
            color = (
                int(40 + progress * 20),
                int(40 + progress * 20),
                int(60 + progress * 30),
                255
            )
            pg.draw.rect(
                self._default_portrait,
                color,
                (0, i, UIConstants.PORTRAIT_SIZE_DIALOG[0], 1)
            )
        
        # Stylized silhouette with glow
        center_x = UIConstants.PORTRAIT_SIZE_DIALOG[0] // 2
        center_y = UIConstants.PORTRAIT_SIZE_DIALOG[1] // 2
        
        # Glow effect
        for i in range(3):
            glow_color = (100 + i * 30, 100 + i * 30, 150 + i * 30, 100 - i * 30)
            pg.draw.circle(self._default_portrait, glow_color, 
                          (center_x, center_y - 20), 35 + i * 3)
        
        # Main silhouette
        pg.draw.circle(self._default_portrait, (180, 180, 220), (center_x, center_y - 20), 30)
        pg.draw.ellipse(self._default_portrait, (160, 160, 200),
                       (center_x - 35, center_y + 10, 70, 50))
        
        # Frame with decorative corners
        frame_rect = self._default_portrait.get_rect().inflate(-4, -4)
        pg.draw.rect(self._default_portrait, (150, 180, 255, 200), frame_rect, 
                    width=3, border_radius=15)
        
        # Corner decorations
        corner_size = 15
        corner_color = (200, 220, 255, 255)
        corners = [
            (4, 4), 
            (UIConstants.PORTRAIT_SIZE_DIALOG[0] - 4 - corner_size, 4),
            (4, UIConstants.PORTRAIT_SIZE_DIALOG[1] - 4 - corner_size),
            (UIConstants.PORTRAIT_SIZE_DIALOG[0] - 4 - corner_size, 
             UIConstants.PORTRAIT_SIZE_DIALOG[1] - 4 - corner_size)
        ]
        for x, y in corners:
            pg.draw.rect(self._default_portrait, corner_color, (x, y, corner_size, 2))
            pg.draw.rect(self._default_portrait, corner_color, (x, y, 2, corner_size))
    
    def _update_animations(self, delta_time: float) -> None:
        """Update all animations."""
        # Update fade animation
        if self._fade_alpha < self._fade_target:
            self._fade_alpha = min(self._fade_target, 
                                 self._fade_alpha + self._fade_speed * delta_time * 60)
        elif self._fade_alpha > self._fade_target:
            self._fade_alpha = max(self._fade_target, 
                                 self._fade_alpha - self._fade_speed * delta_time * 60)
        
        # Update text box slide
        if self._text_box_offset > self._text_box_offset_target:
            self._text_box_offset = max(self._text_box_offset_target,
                                      self._text_box_offset - self._text_box_slide_speed * delta_time * 60)
        elif self._text_box_offset < self._text_box_offset_target:
            self._text_box_offset = min(self._text_box_offset_target,
                                      self._text_box_offset + self._text_box_slide_speed * delta_time * 60)
        
        # Update portrait scale
        if self._portrait_scale < self._portrait_scale_target:
            self._portrait_scale = min(self._portrait_scale_target,
                                     self._portrait_scale + self._portrait_scale_speed * delta_time)
        elif self._portrait_scale > self._portrait_scale_target:
            self._portrait_scale = max(self._portrait_scale_target,
                                     self._portrait_scale - self._portrait_scale_speed * delta_time)
        
        # Update arrow animation
        self._arrow_animation_time += delta_time
    
    def _draw_background_image(self, surface: pg.Surface, image_path: str) -> None:
        """Draw background image for dialog with fade effect."""
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
            
            # Apply fade
            scaled_image.set_alpha(int(self._fade_alpha * 0.8))
            
            # Center on screen
            pos = (
                (self._screen_size[0] - new_size[0]) // 2,
                (self._screen_size[1] - new_size[1]) // 2
            )
            surface.blit(scaled_image, pos)
            
        except (pg.error, FileNotFoundError):
            pass  # Silently ignore missing images
    
    def _draw_name_box(self, surface: pg.Surface, speaker: Optional[str], x_offset: float) -> None:
        """Draw speaker name box with animation."""
        name_bg = self._name_background.copy()
        name_bg.set_alpha(int(self._fade_alpha * 0.95))
        
        name_rect = self._name_box_rect.copy()
        name_rect.x = int(x_offset)
        
        surface.blit(name_bg, name_rect)
        
        speaker_name = speaker or "Narrator"
        name_text = self._name_font.render(speaker_name, True, (240, 240, 255))
        
        # Add text shadow
        shadow_text = self._name_font.render(speaker_name, True, (20, 20, 40))
        shadow_rect = shadow_text.get_rect(center=(name_rect.centerx + 2, name_rect.centery + 2))
        surface.blit(shadow_text, shadow_rect)
        
        # Main text
        text_rect = name_text.get_rect(center=name_rect.center)
        surface.blit(name_text, text_rect)
    
    def _draw_portrait(self, surface: pg.Surface, portrait_path: Optional[str]) -> None:
        """Draw speaker portrait with scale animation and effects."""
        portrait = self._default_portrait
        
        if portrait_path:
            try:
                loaded_portrait = pg.image.load(portrait_path).convert_alpha()
                portrait = pg.transform.scale(loaded_portrait, UIConstants.PORTRAIT_SIZE_DIALOG)
            except (pg.error, FileNotFoundError):
                pass  # Use default portrait
        
        # Apply scale animation
        if self._portrait_scale < 1.0:
            scaled_size = (
                int(UIConstants.PORTRAIT_SIZE_DIALOG[0] * self._portrait_scale),
                int(UIConstants.PORTRAIT_SIZE_DIALOG[1] * self._portrait_scale)
            )
            if scaled_size[0] > 0 and scaled_size[1] > 0:
                portrait = pg.transform.scale(portrait, scaled_size)
                
                # Center the scaled portrait
                scaled_rect = portrait.get_rect(center=self._portrait_rect.center)
                
                # Draw glow effect
                glow_size = (scaled_size[0] + 20, scaled_size[1] + 20)
                glow_surface = pg.Surface(glow_size, pg.SRCALPHA)
                pg.draw.ellipse(glow_surface, (100, 150, 255, 30), glow_surface.get_rect())
                glow_rect = glow_surface.get_rect(center=self._portrait_rect.center)
                surface.blit(glow_surface, glow_rect)
                
                portrait.set_alpha(int(self._fade_alpha))
                surface.blit(portrait, scaled_rect)
        else:
            # Draw full-size portrait with effects
            # Glow effect
            glow_size = (UIConstants.PORTRAIT_SIZE_DIALOG[0] + 20, 
                        UIConstants.PORTRAIT_SIZE_DIALOG[1] + 20)
            glow_surface = pg.Surface(glow_size, pg.SRCALPHA)
            pg.draw.ellipse(glow_surface, (100, 150, 255, 40), glow_surface.get_rect())
            glow_rect = glow_surface.get_rect(center=self._portrait_rect.center)
            surface.blit(glow_surface, glow_rect)
            
            portrait.set_alpha(int(self._fade_alpha))
            surface.blit(portrait, self._portrait_rect)
    
    def _draw_dialog_text(self, surface: pg.Surface, text: str, text_box_y: float) -> None:
        """Draw dialog text with better formatting."""
        # Define text area (accounting for portrait)
        text_area = pg.Rect(
            self._portrait_rect.right + 30,
            text_box_y + 25,
            self._text_box_rect.width - self._portrait_rect.width - 80,
            self._text_box_rect.height - 50
        )
        
        # Word wrapping for full text
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
        
        # Draw all lines with shadow effect
        y = text_area.top
        line_height = self._font.get_height() + 6
        
        for i, line in enumerate(lines):
            if y + line_height > text_area.bottom:
                break  # Text overflow
            
            # Text shadow
            shadow_surface = self._font.render(line, True, (20, 20, 40))
            shadow_surface.set_alpha(int(self._fade_alpha * 0.5))
            surface.blit(shadow_surface, (text_area.left + 2, y + 2))
            
            # Main text
            text_surface = self._font.render(line, True, (255, 255, 255))
            text_surface.set_alpha(int(self._fade_alpha))
            surface.blit(text_surface, (text_area.left, y))
            
            y += line_height
        
        # Store for reference
        self._full_text = text
    
    def _draw_scroll_indicator(self, surface: pg.Surface, text_box_y: float) -> None:
        """Draw animated indicator showing more dialog is available."""
        # Animated arrow with glow
        arrow_y = text_box_y + self._text_box_rect.height - 25
        arrow_x = self._text_box_rect.centerx
        
        # Calculate bounce animation
        bounce = math.sin(self._arrow_animation_time * 3) * 5
        
        # Glow effect
        glow_radius = 20 + math.sin(self._arrow_animation_time * 2) * 5
        glow_surface = pg.Surface((glow_radius * 2, glow_radius * 2), pg.SRCALPHA)
        pg.draw.circle(glow_surface, (100, 150, 255, 50), 
                      (glow_radius, glow_radius), glow_radius)
        glow_rect = glow_surface.get_rect(center=(arrow_x, arrow_y + bounce))
        surface.blit(glow_surface, glow_rect)
        
        # Arrow
        arrow_points = [
            (arrow_x - 12, arrow_y - 8 + bounce),
            (arrow_x + 12, arrow_y - 8 + bounce),
            (arrow_x, arrow_y + 8 + bounce)
        ]
        
        # Arrow shadow
        shadow_points = [(p[0] + 2, p[1] + 2) for p in arrow_points]
        pg.draw.polygon(surface, (20, 20, 40, 100), shadow_points)
        
        # Main arrow
        pg.draw.polygon(surface, (220, 230, 255), arrow_points)
        pg.draw.polygon(surface, (255, 255, 255), arrow_points, 2)
    
    def _advance_dialog(self) -> None:
        """Advance to next dialog entry or hide overlay."""
        if not self._sequence:
            return
        
        # Stop current sound if playing
        self._stop_current_sound()
        
        if self._sequence.is_finished:
            self.hide()
        else:
            self._sequence.advance()
            self._arrow_animation_time = 0.0
            
            # Animate portrait change
            self._portrait_scale = 0.8
            self._portrait_scale_target = 1.0
            
            # Update text
            entry = self._sequence.current_entry
            self._full_text = entry.text
            
            # Play sound for new entry if specified
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