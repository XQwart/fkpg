"""Fallen Knight - Main entry point."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

import pygame as pg

from src.models.config import Config
from src.controllers.scene_manager import SceneManager
from src.core.exceptions import GameError


def main() -> None:
    """Main game entry point."""
    try:
        # Initialize Pygame
        pg.init()
        pg.mixer.init()
        
        # Create configuration
        config = Config()
        
        # Create display
        config.create_display()
        
        # Create and run scene manager
        scene_manager = SceneManager(config)
        scene_manager.run()
        
    except GameError as e:
        print(f"Game error: {e}")
        return
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return
        
    finally:
        # Clean up
        if 'config' in locals():
            config.save()
        
        pg.quit()


if __name__ == "__main__":
    main()