"""Game scene controller with gameplay logic."""
from __future__ import annotations

from typing import Optional, Tuple
from pathlib import Path
import pygame as pg

from src.controllers.base.scene import BaseScene
from src.views.renderers.game_renderer import GameRenderer
from src.views.ui.dialog_overlay import DialogOverlay
from src.models.entities.player import Player, PlayerAction
from src.models.world.level import Level
from src.models.ui.dialog import get_dialog_manager
from src.models.config import Config
from src.core.constants import AssetPaths, GRAVITY, MAX_FALL_SPEED, SAVE_FILE
from src.core.exceptions import LevelError
from src.core.cache_manager import get_cache_manager


class GameScene(BaseScene):
    """Main gameplay scene with physics and rendering."""
    
    def __init__(
        self,
        config: Config,
        level_id: str = "tutorial",
        saved_data: Optional[Tuple[float, float, int]] = None
    ) -> None:
        """
        Initialize game scene.
        
        Args:
            config: Game configuration
            level_id: Level to load
            saved_data: Optional saved player data (x, y, health)
        """
        super().__init__(config)
        
        # Create renderer and overlay
        self._renderer = GameRenderer()
        self._dialog_overlay = DialogOverlay()
        
        # Load level
        self._level_id = level_id
        self._level = self._load_level(level_id)
        
        # Create player
        if saved_data:
            x, y, health = saved_data
            self._player = Player(x, y, health)
        else:
            spawn = self._level.spawn_point
            self._player = Player(spawn.x, spawn.y)
        
        # Entity management
        self._entities = pg.sprite.Group()
        self._entities.add(self._player)
        
        # Input mapping
        self._create_input_mapping()
        
        # Game state
        self._paused = False
        self._debug_mode = False
        
        # Cache manager
        self._cache_manager = get_cache_manager()
    
    def handle_events(self) -> Optional[str]:
        """Process game input events."""
        for event in pg.event.get():
            # Let dialog overlay handle events first
            if self._dialog_overlay.is_visible():
                if self._dialog_overlay.handle_event(event):
                    continue
            
            # Handle common events
            action = self._handle_common_events(event)
            if action:
                return action
            
            # Handle game-specific events
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    return "menu"
                
                elif event.key == pg.K_F3:
                    self._debug_mode = not self._debug_mode
                    self._renderer.toggle_debug_mode()
                
                elif event.key == pg.K_p and not self._dialog_overlay.is_visible():
                    self._paused = not self._paused
                
                # Handle player input
                elif not self._paused and not self._dialog_overlay.is_visible():
                    self._handle_key_down(event.key)
            
            elif event.type == pg.KEYUP:
                if not self._paused and not self._dialog_overlay.is_visible():
                    self._handle_key_up(event.key)
            
            elif event.type == pg.MOUSEBUTTONDOWN:
                if not self._paused and not self._dialog_overlay.is_visible():
                    self._player.handle_mouse_click(event.button, pg.time.get_ticks())
        
        return None
    
    def update(self, delta_time: float) -> None:
        """Update game state."""
        # Update cache manager
        self._cache_manager.update()
        
        # Don't update if paused or dialog active
        if self._paused or self._dialog_overlay.is_visible():
            return
        
        # Update entities (this will call player's custom update method)
        self._entities.update(delta_time)
        
        # Apply physics manually for player and handle collisions
        self._move_and_collide(delta_time)
        
        # Update camera
        self._renderer.camera.set_follow_target(self._player)
        self._renderer.camera.update(delta_time)
        
        # Check triggers
        self._check_triggers()
        
        # Check game over conditions
        if not self._player.is_alive:
            return "game_over"
    
    def render(self) -> None:
        """Render game scene."""
        # Render game world
        self._renderer.render(self.screen, self._level, self._entities, self._player)
        
        # Render dialog overlay if active
        if self._dialog_overlay.is_visible():
            self._dialog_overlay.render(self.screen)
        
        # Render pause overlay
        if self._paused and not self._dialog_overlay.is_visible():
            self._render_pause_overlay()
    
    def on_enter(self) -> None:
        """Called when entering game scene."""
        super().on_enter()
        
        # Initialize renderer
        self._renderer.initialize(self.screen)
        self._renderer.camera.set_world_bounds(self._level.bounds)
        
        # Update dialog overlay screen size
        self._dialog_overlay.update_screen_size(
            self.screen.get_width(),
            self.screen.get_height()
        )
        
        # Stop menu music
        pg.mixer.music.stop()
        
        # Check for level intro dialog
        self._check_intro_dialog()
    
    def on_exit(self) -> None:
        """Called when exiting game scene."""
        super().on_exit()
        
        # Save game state
        self._save_game()
        
        # Clean up resources
        self._entities.empty()
        
        # Clean up level
        if hasattr(self._level, 'cleanup'):
            self._level.cleanup()
    
    def _create_input_mapping(self) -> None:
        """Create input action mappings."""
        kb = self.config.key_bindings
        
        self._key_down_actions = {
            kb.left: lambda: self._player.handle_action(PlayerAction.MOVE_LEFT, True),
            kb.right: lambda: self._player.handle_action(PlayerAction.MOVE_RIGHT, True),
            kb.jump: lambda: self._player.handle_action(PlayerAction.JUMP, True),
            kb.sprint: lambda: self._player.handle_action(PlayerAction.SPRINT, True),
            kb.block: lambda: self._player.handle_action(PlayerAction.BLOCK, True),
        }
        
        self._key_up_actions = {
            kb.left: lambda: self._player.handle_action(PlayerAction.MOVE_LEFT, False),
            kb.right: lambda: self._player.handle_action(PlayerAction.MOVE_RIGHT, False),
            kb.sprint: lambda: self._player.handle_action(PlayerAction.SPRINT, False),
            kb.block: lambda: self._player.handle_action(PlayerAction.BLOCK, False),
        }
    
    def _handle_key_down(self, key: int) -> None:
        """Handle key down event."""
        action = self._key_down_actions.get(key)
        if action:
            action()
    
    def _handle_key_up(self, key: int) -> None:
        """Handle key up event."""
        action = self._key_up_actions.get(key)
        if action:
            action()
    
    def _load_level(self, level_id: str) -> Level:
        """Load level from file."""
        level = Level(level_id)
        tmx_path = Path(AssetPaths.GAME_LEVELS) / level_id / f"{level_id}.tmx"
        
        try:
            level.load_from_tmx(tmx_path)
            return level
        except LevelError as e:
            # Return empty level on error
            print(f"Failed to load level {level_id}: {e}")
            return level
    
    def _move_and_collide(self, delta_time: float) -> None:
        """Handle player movement, physics, and collisions by axis."""
        player = self._player
        
        # 1. Apply acceleration to velocity (from player's update)
        player.velocity += player.acceleration * delta_time
        
        # Clamp velocity to maximum values
        max_vel = player.max_velocity
        player.velocity.x = max(-max_vel.x, min(player.velocity.x, max_vel.x))
        player.velocity.y = max(-max_vel.y, min(player.velocity.y, max_vel.y))
        
        # Store position before vertical movement for platform check
        original_y = player.position.y
        
        # Get collidable geometry using cached groups
        collidable_tiles = self._level.get_all_collidable_tiles()
        platform_tiles = self._level.get_all_platform_tiles()
        hazard_tiles = self._level.get_all_hazard_tiles()
        
        # 2. Horizontal movement and collision
        player.position.x += player.velocity.x * delta_time
        player.rect.centerx = int(player.position.x)
        
        hit_list = pg.sprite.spritecollide(player, collidable_tiles, dokill=False)
        for tile in hit_list:
            if player.velocity.x > 0:  # Moving right
                player.rect.right = tile.rect.left
            elif player.velocity.x < 0:  # Moving left
                player.rect.left = tile.rect.right
            player.position.x = float(player.rect.centerx)
            player.velocity.x = 0
            
        # 3. Vertical movement and collision
        # Capture initial vertical velocity direction BEFORE movement for proper collision resolution
        vy_initial = player.velocity.y
        player.position.y += player.velocity.y * delta_time
        player.rect.centery = int(player.position.y)

        player.on_ground = False
        
        # Check for solid tile collisions
        hit_list = pg.sprite.spritecollide(player, collidable_tiles, dokill=False)
        if vy_initial > 0:  # Falling downward
            for tile in hit_list:
                player.rect.bottom = tile.rect.top
                player.on_ground = True
                player.velocity.y = 0
                player.position.y = float(player.rect.centery)
        elif vy_initial < 0:  # Moving upward (head bump)
            for tile in hit_list:
                player.rect.top = tile.rect.bottom
                player.velocity.y = 0
                player.position.y = float(player.rect.centery)
        else:
            # vy_initial == 0 (edge case) – treat as downward for stability
            for tile in hit_list:
                player.rect.bottom = tile.rect.top
                player.on_ground = True
                player.velocity.y = 0
                player.position.y = float(player.rect.centery)

        # 4. One-way platform collision
        if player.velocity.y >= 0:
            # Don't check for platforms if already on solid ground
            if not player.on_ground:
                platform_hits = pg.sprite.spritecollide(player, platform_tiles, dokill=False)
                for platform in platform_hits:
                    # Player's feet must be above the platform's top and not passing up through it
                    is_passing_through = original_y + player.rect.height / 2 > platform.rect.top + 1
                    if player.rect.bottom > platform.rect.top and not is_passing_through:
                        player.rect.bottom = platform.rect.top
                        player.on_ground = True
                        player.velocity.y = 0
                        player.position.y = float(player.rect.centery)

        # Non-intrusive ground adjacency check (1px below)
        if not player.on_ground and player.velocity.y == 0:
            test_rect = player.rect.move(0, 1)
            ground_tiles = collidable_tiles.sprites() + platform_tiles.sprites()
            for tile in ground_tiles:
                if test_rect.colliderect(tile.rect):
                    player.on_ground = True
                    break

        # 5. Hazard collision
        if pg.sprite.spritecollide(player, hazard_tiles, dokill=False):
            if not player.is_invulnerable:
                player.take_damage(10)
    
    def _check_triggers(self) -> None:
        """Check for trigger tile activation."""
        # Get all trigger groups from level
        for trigger_id in ["dialog", "checkpoint", "exit"]:
            trigger_tiles = self._level.get_all_trigger_tiles(trigger_id)
            
            if pg.sprite.spritecollide(self._player, trigger_tiles, False):
                self._activate_trigger(trigger_id)
    
    def _activate_trigger(self, trigger_id: str) -> None:
        """Activate a trigger."""
        if trigger_id == "dialog":
            self._show_dialog("test_dialog")
        elif trigger_id == "checkpoint":
            self._save_checkpoint()
        elif trigger_id == "exit":
            self._complete_level()
    
    def _check_intro_dialog(self) -> None:
        """Check if level has intro dialog."""
        dialog_manager = get_dialog_manager()
        dialog_path = Path(AssetPaths.GAME_DIALOGS) / f"{self._level_id}_intro.json"
        
        if dialog_path.exists():
            try:
                sequence = dialog_manager.load_sequence_from_file(
                    f"{self._level_id}_intro",
                    dialog_path
                )
                self._dialog_overlay.set_sequence(sequence)
            except Exception:
                pass  # Silently ignore dialog errors
    
    def _show_dialog(self, dialog_id: str) -> None:
        """Show in-game dialog."""
        dialog_manager = get_dialog_manager()
        sequence = dialog_manager.get_sequence(dialog_id)
        
        if sequence:
            self._dialog_overlay.set_sequence(sequence)
    
    def _save_checkpoint(self) -> None:
        """Save current checkpoint."""
        # TODO: Implement checkpoint saving
        pass
    
    def _complete_level(self) -> None:
        """Complete current level and transition."""
        # TODO: Implement level completion
        self.transition_to("level_complete")
    
    def _save_game(self) -> None:
        """Save current game state."""
        save_data = f"{int(self._player.position.x)} {int(self._player.position.y)} {self._player.health}"
        
        try:
            with open(SAVE_FILE, 'w') as f:
                f.write(save_data)
        except IOError:
            pass  # Silently ignore save errors
    
    def _render_pause_overlay(self) -> None:
        """Render pause screen overlay."""
        # Darken screen
        overlay = pg.Surface(self.screen.get_size())
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # Draw pause text
        font = pg.font.Font(None, 72)
        text = font.render("PAUSED", True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
        self.screen.blit(text, text_rect)
        
        # Draw instructions
        instruction_font = pg.font.Font(None, 36)
        instruction = instruction_font.render("Press P to resume", True, (200, 200, 200))
        instruction_rect = instruction.get_rect(center=(self.screen.get_width() // 2, text_rect.bottom + 40))
        self.screen.blit(instruction, instruction_rect)