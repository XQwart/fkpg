"""Scene manager for coordinating scene transitions."""
from __future__ import annotations

from typing import Dict, Optional, Type
from pathlib import Path
import gc

from src.controllers.base.scene import BaseScene
from src.controllers.scenes.menu_scene import MenuScene
from src.controllers.scenes.game_scene import GameScene
from src.controllers.scenes.settings_scene import SettingsScene
from src.controllers.scenes.dialog_scene import DialogScene
from src.models.config import Config
from src.core.constants import SAVE_FILE
from src.core.exceptions import SceneError
from src.core.cache_manager import get_cache_manager


class SceneManager:
    """Manages scene creation and transitions."""
    
    def __init__(self, config: Config) -> None:
        """Initialize scene manager."""
        self._config = config
        self._current_scene: Optional[BaseScene] = None
        self._scene_cache: Dict[str, BaseScene] = {}
        
        # Scene registry
        self._scene_classes: Dict[str, Type[BaseScene]] = {
            "menu": MenuScene,
            "settings": SettingsScene,
            "game": GameScene,
            "dialog": DialogScene,
        }
        
        # Game state
        self._current_level = "tutorial"
        self._saved_data = None
        
        # Cache manager
        self._cache_manager = get_cache_manager()
    
    def run(self) -> None:
        """Run the game loop with scene management."""
        # Start with menu
        current_scene_id = "menu"
        previous_scene = None
        
        while current_scene_id and current_scene_id != "exit":
            # Get or create scene
            scene = self._get_scene(current_scene_id)
            
            if not scene:
                raise SceneError(f"Unknown scene: {current_scene_id}")
            
            # Clean up previous scene if different
            if previous_scene and previous_scene != scene:
                self._cleanup_scene(previous_scene)
            
            # Run scene and get next scene ID
            next_scene_id = scene.run()
            
            # Handle special transitions
            previous_scene = scene
            current_scene_id = self._handle_transition(current_scene_id, next_scene_id)
        
        # Final cleanup
        if previous_scene:
            self._cleanup_scene(previous_scene)
        self._cleanup()
    
    def _get_scene(self, scene_id: str) -> Optional[BaseScene]:
        """Get or create a scene by ID."""
        # Handle special scene IDs
        if scene_id == "new_game":
            # Clear save and start intro dialog
            self._saved_data = None
            self._current_level = "tutorial"
            return self._create_scene("dialog", dialog_id="introduction", next_scene="game")
        
        elif scene_id == "continue":
            # Load saved game
            self._load_saved_game()
            return self._create_scene("game", level_id=self._current_level, saved_data=self._saved_data)
        
        elif scene_id == "game":
            # Create game scene with current state
            return self._create_scene("game", level_id=self._current_level, saved_data=self._saved_data)
        
        # Check cache for reusable scenes
        if scene_id in ["menu", "settings"]:
            if scene_id not in self._scene_cache:
                self._scene_cache[scene_id] = self._create_scene(scene_id)
            return self._scene_cache[scene_id]
        
        # Create new scene
        return self._create_scene(scene_id)
    
    def _create_scene(self, scene_id: str, **kwargs) -> Optional[BaseScene]:
        """Create a new scene instance."""
        scene_class = self._scene_classes.get(scene_id)
        
        if not scene_class:
            return None
        
        try:
            # Create scene with appropriate arguments
            if scene_id == "game":
                return scene_class(
                    self._config,
                    level_id=kwargs.get("level_id", self._current_level),
                    saved_data=kwargs.get("saved_data")
                )
            elif scene_id == "dialog":
                return scene_class(
                    self._config,
                    dialog_id=kwargs.get("dialog_id", "test"),
                    next_scene=kwargs.get("next_scene", "menu")
                )
            else:
                return scene_class(self._config)
                
        except Exception as e:
            raise SceneError(f"Failed to create scene {scene_id}: {e}")
    
    def _handle_transition(self, from_scene: str, to_scene: Optional[str]) -> Optional[str]:
        """Handle special scene transitions."""
        if not to_scene:
            return None
        
        # Map action strings to scene IDs
        transition_map = {
            "exit": None,
            "menu": "menu",
            "settings": "settings",
            "back": "menu",
            "new_game": "new_game",
            "continue": "continue",
            "game": "game",
            "game_over": "menu",  # TODO: Add game over scene
            "level_complete": "menu",  # TODO: Add level complete scene
        }
        
        return transition_map.get(to_scene, to_scene)
    
    def _load_saved_game(self) -> None:
        """Load saved game data."""
        try:
            save_path = Path(SAVE_FILE)
            if save_path.exists():
                with open(save_path, 'r') as f:
                    data = f.read().strip().split()
                    if len(data) >= 3:
                        x = float(data[0])
                        y = float(data[1])
                        health = int(data[2])
                        self._saved_data = (x, y, health)
                        
                        # Load level ID if available
                        if len(data) >= 4:
                            self._current_level = data[3]
        except (IOError, ValueError):
            self._saved_data = None
    
    def _cleanup_scene(self, scene: BaseScene) -> None:
        """Clean up resources for a scene."""
        # Don't clean up cached scenes (menu, settings)
        scene_type = type(scene).__name__.lower().replace("scene", "")
        if scene_type in ["menu", "settings"]:
            return
        
        # For game scenes, clear certain caches
        if isinstance(scene, GameScene):
            # Clear collision caches (they have TTL anyway)
            collision_cache = self._cache_manager.get_cache("collision_groups")
            if collision_cache:
                collision_cache.clear()
            
            # Optionally clear tile surface cache if memory is high
            total_memory = self._cache_manager.get_total_memory()
            if total_memory > 150 * 1024 * 1024:  # 150MB threshold
                tile_cache = self._cache_manager.get_cache("tile_surfaces")
                if tile_cache:
                    # Remove oldest entries to free up space
                    while tile_cache._total_memory > 30 * 1024 * 1024:  # Keep max 30MB
                        if not tile_cache._evict_one():
                            break
        
        # Force garbage collection for large scenes
        gc.collect()
    
    def _cleanup(self) -> None:
        """Clean up all resources."""
        # Clear scene cache
        self._scene_cache.clear()
        
        # Save configuration
        self._config.save()
        
        # Clear all caches
        self._cache_manager.clear_all()
        
        # Force final garbage collection
        gc.collect()