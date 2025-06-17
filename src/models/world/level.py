"""Level model for game world management."""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import pygame as pg
import pytmx

from src.models.world.tile import Tile, TileProperties, AnimatedTile, TriggerTile
from src.core.constants import TILE_SIZE
from src.core.exceptions import LevelError
from src.core.cache_manager import get_cache_manager


class TileLayer:
    """A single layer of tiles in the level."""
    
    def __init__(self, name: str, layer_index: int = 0) -> None:
        """
        Initialize tile layer.
        
        Args:
            name: Layer name
            layer_index: Drawing order index
        """
        self._name = name
        self._layer_index = layer_index
        self._tiles = pg.sprite.Group()
        self._collidable_tiles = pg.sprite.Group()
        self._hazard_tiles = pg.sprite.Group()
        self._platform_tiles = pg.sprite.Group()
        self._trigger_tiles: Dict[str, pg.sprite.Group] = {}
        self._visible = True
        self._opacity = 1.0
        
        # Fast lookup map grid_position -> tile for visibility queries
        self._tile_map: Dict[tuple[int, int], Tile] = {}
    
    @property
    def name(self) -> str:
        """Get layer name."""
        return self._name
    
    @property
    def layer_index(self) -> int:
        """Get layer drawing order."""
        return self._layer_index
    
    @property
    def visible(self) -> bool:
        """Check if layer is visible."""
        return self._visible
    
    @visible.setter
    def visible(self, value: bool) -> None:
        """Set layer visibility."""
        self._visible = value
    
    @property
    def opacity(self) -> float:
        """Get layer opacity (0.0 to 1.0)."""
        return self._opacity
    
    @opacity.setter
    def opacity(self, value: float) -> None:
        """Set layer opacity."""
        self._opacity = max(0.0, min(1.0, value))
    
    def add_tile(self, tile: Tile) -> None:
        """Add tile to appropriate groups based on properties."""
        self._tiles.add(tile)
        
        if tile.is_collidable:
            self._collidable_tiles.add(tile)
        
        if tile.is_hazardous:
            self._hazard_tiles.add(tile)
        
        if tile.is_platform:
            self._platform_tiles.add(tile)
        
        if tile.trigger_id:
            if tile.trigger_id not in self._trigger_tiles:
                self._trigger_tiles[tile.trigger_id] = pg.sprite.Group()
            self._trigger_tiles[tile.trigger_id].add(tile)
        
        # Index for fast lookup
        self._tile_map[tile.grid_position] = tile
    
    @property
    def all_tiles(self) -> pg.sprite.Group:
        """Get all tiles in layer."""
        return self._tiles
    
    @property
    def collidable_tiles(self) -> pg.sprite.Group:
        """Get collidable tiles."""
        return self._collidable_tiles
    
    @property
    def hazard_tiles(self) -> pg.sprite.Group:
        """Get hazardous tiles."""
        return self._hazard_tiles
    
    @property
    def platform_tiles(self) -> pg.sprite.Group:
        """Get platform tiles."""
        return self._platform_tiles
    
    def get_trigger_tiles(self, trigger_id: str) -> pg.sprite.Group:
        """Get tiles for specific trigger."""
        return self._trigger_tiles.get(trigger_id, pg.sprite.Group())
    
    def get_tile_at(self, gx: int, gy: int) -> Optional[Tile]:
        """Get tile at grid coordinate if present."""
        return self._tile_map.get((gx, gy))
    
    def remove_tile_at(self, grid_x: int, grid_y: int) -> bool:
        """Remove tile at specific grid position."""
        tile = self.get_tile_at(grid_x, grid_y)
        if tile:
            tile.kill()
            return True
        return False
    
    def cleanup(self) -> None:
        """Clean up layer resources."""
        self._tiles.empty()
        self._collidable_tiles.empty()
        self._hazard_tiles.empty()
        self._platform_tiles.empty()
        for group in self._trigger_tiles.values():
            group.empty()
        self._trigger_tiles.clear()
        self._tile_map.clear()


class Level:
    """Complete game level with multiple layers and properties."""
    
    def __init__(self, level_id: str) -> None:
        """Initialize level with given ID."""
        self._level_id = level_id
        self._layers: Dict[str, TileLayer] = {}
        self._layer_order: List[str] = []
        self._spawn_points: Dict[str, pg.math.Vector2] = {}
        self._bounds = pg.Rect(0, 0, 1000, 1000)
        self._background_color = (50, 50, 70)
        self._ambient_light = (255, 255, 255)
        self._properties: Dict[str, any] = {}
        self._tmx_data: Optional[pytmx.TiledMap] = None
        self._tile_size = TILE_SIZE
        self._entities_to_spawn: List[Dict] = []
        
        # Use centralized cache manager
        self._cache_manager = get_cache_manager()
        self._cache_key_prefix = f"level_{level_id}"
    
    @property
    def level_id(self) -> str:
        """Get level identifier."""
        return self._level_id
    
    @property
    def spawn_point(self) -> pg.math.Vector2:
        """Get default spawn point."""
        return self._spawn_points.get('default', pg.math.Vector2(500, 950))
    
    @property
    def bounds(self) -> pg.Rect:
        """Get level boundaries."""
        return self._bounds.copy()
    
    @property
    def background_color(self) -> Tuple[int, int, int]:
        """Get background color."""
        return self._background_color
    
    @property
    def ambient_light(self) -> Tuple[int, int, int]:
        """Get ambient light color."""
        return self._ambient_light
    
    @property
    def tile_size(self) -> int:
        """Get tile size in pixels."""
        return self._tile_size
    
    @property
    def width_in_tiles(self) -> int:
        """Get level width in tiles."""
        return self._bounds.width // self._tile_size
    
    @property
    def height_in_tiles(self) -> int:
        """Get level height in tiles."""
        return self._bounds.height // self._tile_size
    
    @property
    def entities_to_spawn(self) -> List[Dict]:
        """Get list of entities to spawn in level."""
        return self._entities_to_spawn.copy()
    
    def load_from_tmx(self, tmx_path: Path) -> None:
        """Load level from TMX file."""
        if not tmx_path.exists():
            raise LevelError(f"Level file not found: {tmx_path}")
        
        try:
            self._tmx_data = pytmx.load_pygame(str(tmx_path))
            self._load_level_properties()
            self._create_tile_layers()
            self._load_object_layers()
            
            # Invalidate collision caches when level is loaded
            self._invalidate_collision_cache()
            
        except Exception as e:
            raise LevelError(f"Failed to load level from {tmx_path}: {e}")
    
    def get_layer(self, name: str) -> Optional[TileLayer]:
        """Get layer by name."""
        return self._layers.get(name)
    
    def get_layers_in_order(self) -> List[TileLayer]:
        """Get all layers in drawing order."""
        return [self._layers[name] for name in self._layer_order if name in self._layers]
    
    def get_spawn_point(self, name: str = 'default') -> Optional[pg.math.Vector2]:
        """Get named spawn point."""
        return self._spawn_points.get(name)
    
    def add_spawn_point(self, name: str, position: pg.math.Vector2) -> None:
        """Add or update spawn point."""
        self._spawn_points[name] = position.copy()
    
    def get_property(self, key: str, default: any = None) -> any:
        """Get level property."""
        return self._properties.get(key, default)
    
    def set_property(self, key: str, value: any) -> None:
        """Set level property."""
        self._properties[key] = value
    
    def get_all_collidable_tiles(self) -> pg.sprite.Group:
        """Get all collidable tiles from all layers with caching."""
        cache_key = f"{self._cache_key_prefix}_collidable"
        cached_group = self._cache_manager.get("collision_groups", cache_key)
        
        if cached_group is None:
            cached_group = pg.sprite.Group()
            for layer in self._layers.values():
                if layer.visible:
                    cached_group.add(layer.collidable_tiles)
            self._cache_manager.put("collision_groups", cache_key, cached_group, ttl=5.0)
        
        return cached_group
    
    def get_all_hazard_tiles(self) -> pg.sprite.Group:
        """Get all hazard tiles from all layers with caching."""
        cache_key = f"{self._cache_key_prefix}_hazard"
        cached_group = self._cache_manager.get("collision_groups", cache_key)
        
        if cached_group is None:
            cached_group = pg.sprite.Group()
            for layer in self._layers.values():
                if layer.visible:
                    cached_group.add(layer.hazard_tiles)
            self._cache_manager.put("collision_groups", cache_key, cached_group, ttl=5.0)
        
        return cached_group
    
    def get_all_platform_tiles(self) -> pg.sprite.Group:
        """Get all platform tiles from all layers with caching."""
        cache_key = f"{self._cache_key_prefix}_platform"
        cached_group = self._cache_manager.get("collision_groups", cache_key)
        
        if cached_group is None:
            cached_group = pg.sprite.Group()
            for layer in self._layers.values():
                if layer.visible:
                    cached_group.add(layer.platform_tiles)
            self._cache_manager.put("collision_groups", cache_key, cached_group, ttl=5.0)
        
        return cached_group
    
    def get_all_trigger_tiles(self, trigger_id: str) -> pg.sprite.Group:
        """Get all trigger tiles with specific ID from all layers with caching."""
        cache_key = f"{self._cache_key_prefix}_trigger_{trigger_id}"
        cached_group = self._cache_manager.get("collision_groups", cache_key)
        
        if cached_group is None:
            cached_group = pg.sprite.Group()
            for layer in self._layers.values():
                if layer.visible:
                    cached_group.add(layer.get_trigger_tiles(trigger_id))
            self._cache_manager.put("collision_groups", cache_key, cached_group, ttl=5.0)
        
        return cached_group
    
    def get_visible_tiles(self, camera_rect: pg.Rect) -> List[Tuple[Tile, TileLayer]]:
        """Get tiles visible in camera view with their layers (indexed lookup)."""
        visible_tiles: list[tuple[Tile, TileLayer]] = []
        
        # Calculate tile range around camera viewport with 1-tile padding
        start_x = max(0, camera_rect.left // self._tile_size - 1)
        end_x = min(self.width_in_tiles - 1, camera_rect.right // self._tile_size + 1)
        start_y = max(0, camera_rect.top // self._tile_size - 1)
        end_y = min(self.height_in_tiles - 1, camera_rect.bottom // self._tile_size + 1)
        
        for layer in self.get_layers_in_order():
            if not layer.visible:
                continue
            for gx in range(start_x, end_x + 1):
                for gy in range(start_y, end_y + 1):
                    tile = layer.get_tile_at(gx, gy)
                    if tile is not None:
                        visible_tiles.append((tile, layer))
        return visible_tiles
    
    def get_tile_at_position(self, world_x: float, world_y: float, layer_name: Optional[str] = None) -> Optional[Tile]:
        """Get tile at world position."""
        grid_x = int(world_x // self._tile_size)
        grid_y = int(world_y // self._tile_size)
        
        if layer_name:
            layer = self.get_layer(layer_name)
            return layer.get_tile_at(grid_x, grid_y) if layer else None
        
        # Check all layers from top to bottom
        for layer_name in reversed(self._layer_order):
            layer = self._layers.get(layer_name)
            if layer and layer.visible:
                tile = layer.get_tile_at(grid_x, grid_y)
                if tile:
                    return tile
        
        return None
    
    def cleanup(self) -> None:
        """Clean up level resources."""
        # Clear all layers
        for layer in self._layers.values():
            layer.cleanup()
        self._layers.clear()
        self._layer_order.clear()
        
        # Invalidate all caches related to this level
        self._invalidate_collision_cache()
    
    def _invalidate_collision_cache(self) -> None:
        """Invalidate collision-related caches."""
        # Remove all collision caches for this level
        cache_keys = [
            f"{self._cache_key_prefix}_collidable",
            f"{self._cache_key_prefix}_hazard", 
            f"{self._cache_key_prefix}_platform"
        ]
        
        # Also invalidate trigger caches
        for layer in self._layers.values():
            for trigger_id in layer._trigger_tiles.keys():
                cache_keys.append(f"{self._cache_key_prefix}_trigger_{trigger_id}")
        
        # Clear from cache
        collision_cache = self._cache_manager.get_cache("collision_groups")
        if collision_cache:
            for key in cache_keys:
                collision_cache.remove(key)
    
    def _load_level_properties(self) -> None:
        """Load properties from TMX data."""
        if not self._tmx_data:
            return
        
        # Set level bounds
        self._tile_size = self._tmx_data.tilewidth
        self._bounds = pg.Rect(
            0, 0,
            self._tmx_data.width * self._tile_size,
            self._tmx_data.height * self._tile_size
        )
        
        # Load properties
        props = self._tmx_data.properties
        
        # Background color
        if 'background_color' in props:
            self._background_color = self._parse_color(props['background_color'])
        
        # Ambient light
        if 'ambient_light' in props:
            self._ambient_light = self._parse_color(props['ambient_light'])
        
        # Copy all properties
        self._properties = dict(props)
    
    def _create_tile_layers(self) -> None:
        """Create tile layers from TMX data."""
        if not self._tmx_data:
            return
        
        layer_index = 0
        
        for tmx_layer in self._tmx_data.visible_layers:
            if isinstance(tmx_layer, pytmx.TiledTileLayer):
                tile_layer = TileLayer(tmx_layer.name, layer_index)
                tile_layer.visible = tmx_layer.visible
                tile_layer.opacity = tmx_layer.opacity
                
                # Create tiles
                for x, y, gid in tmx_layer:
                    if gid == 0:  # Empty tile
                        continue
                    
                    tile_image = self._tmx_data.get_tile_image_by_gid(gid)
                    if not tile_image:
                        continue
                    
                    # Get tile properties
                    props = self._tmx_data.get_tile_properties_by_gid(gid) or {}
                    tile_props = TileProperties.from_tmx_properties(props)
                    
                    # Scale image if needed
                    if tile_image.get_size() != (self._tile_size, self._tile_size):
                        tile_image = pg.transform.scale(tile_image, (self._tile_size, self._tile_size))
                    
                    # Create appropriate tile type
                    if tile_props.trigger:
                        tile = TriggerTile(
                            x, y, self._tile_size, tile_image,
                            tile_props.trigger, props, tile_props, gid
                        )
                    else:
                        tile = Tile(x, y, self._tile_size, tile_image, tile_props, gid)
                    
                    tile_layer.add_tile(tile)
                
                self._layers[tmx_layer.name] = tile_layer
                self._layer_order.append(tmx_layer.name)
                layer_index += 1
    
    def _load_object_layers(self) -> None:
        """Load object layers for spawn points and entities."""
        if not self._tmx_data:
            return
        
        for tmx_layer in self._tmx_data.visible_layers:
            if isinstance(tmx_layer, pytmx.TiledObjectGroup):
                for obj in tmx_layer:
                    self._process_object(obj)
    
    def _process_object(self, obj: pytmx.TiledObject) -> None:
        """Process TMX object."""
        obj_type = obj.type or obj.name
        
        if obj_type == 'spawn_point':
            spawn_name = obj.name or 'default'
            self.add_spawn_point(spawn_name, pg.math.Vector2(obj.x, obj.y))
        
        elif obj_type in ['entity', 'npc', 'enemy', 'item']:
            entity_data = {
                'type': obj_type,
                'name': obj.name,
                'position': (obj.x, obj.y),
                'properties': dict(obj.properties) if obj.properties else {}
            }
            self._entities_to_spawn.append(entity_data)
    
    def _parse_color(self, color_str: str) -> Tuple[int, int, int]:
        """Parse color string to RGB tuple."""
        if color_str.startswith('#'):
            color_str = color_str[1:]
            if len(color_str) == 6:
                r = int(color_str[0:2], 16)
                g = int(color_str[2:4], 16)
                b = int(color_str[4:6], 16)
                return (r, g, b)
        
        try:
            parts = color_str.split(',')
            if len(parts) == 3:
                return (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            pass
        
        return (50, 50, 70)  # Default color