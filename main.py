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
from src.core.cache_manager import get_cache_manager


def main() -> None:
    """Main game entry point."""
    cache_manager = None
    
    try:
        # Initialize Pygame
        pg.init()
        pg.mixer.init()
        
        # Create configurationabstract_entity.py
        config = Config()
        
        # Create display
        config.create_display()
        
        # Initialize cache manager
        cache_manager = get_cache_manager()
        
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
        
        # Shutdown cache manager
        if cache_manager:
            # Print cache statistics for debugging
            if __debug__:
                stats = cache_manager.get_stats()
                print("\nCache Statistics:")
                print(f"Total Memory: {stats['total_memory'] / (1024 * 1024):.2f} MB")
                for cache_name, cache_stats in stats['caches'].items():
                    print(f"\n{cache_name}:")
                    print(f"  Size: {cache_stats['size']} items")
                    print(f"  Memory: {cache_stats['memory'] / (1024 * 1024):.2f} MB")
                    print(f"  Hit Rate: {cache_stats['hit_rate']:.2%}")
            
            cache_manager.shutdown()
        
        pg.quit()


if __name__ == "__main__":
    main()