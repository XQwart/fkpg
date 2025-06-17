"""Core constants for the Fallen Knight game."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


# Display constants
WINDOW_TITLE: Final[str] = "Fallen Knight"
DEFAULT_WINDOW_WIDTH: Final[int] = 1280
DEFAULT_WINDOW_HEIGHT: Final[int] = 720
MIN_WINDOW_WIDTH: Final[int] = 960
MIN_WINDOW_HEIGHT: Final[int] = 540

# Tile and world constants
TILE_SIZE: Final[int] = 64
DEFAULT_MAP_WIDTH_TILES: Final[int] = 100
DEFAULT_MAP_HEIGHT_TILES: Final[int] = 100

# Physics constants
GRAVITY: Final[float] = 2160.0  # pixels per second squared (was 0.6 * 60 * 60)
JUMP_SPEED: Final[float] = -720.0  # pixels per second (was -12.0 * 60)
MAX_FALL_SPEED: Final[float] = 1080.0  # pixels per second (was 18.0 * 60)
BASE_MOVEMENT_SPEED: Final[float] = 240.0  # pixels per second (was 4.0 * 60)
SPRINT_MULTIPLIER: Final[float] = 1.2

# Camera constants
CAMERA_LERP_FACTOR: Final[float] = 0.20

# Input constants
DOUBLE_CLICK_THRESHOLD_MS: Final[int] = 250

# UI constants
HUD_PADDING: Final[int] = 50
HUD_ELEMENT_MARGIN: Final[int] = 10
DIALOG_TEXT_BOX_HEIGHT_RATIO: Final[float] = 0.30
DIALOG_PADDING: Final[int] = 40

# Visual constants
BACKGROUND_COLOR: Final[tuple[int, int, int]] = (50, 50, 70)
UI_BACKGROUND_ALPHA: Final[int] = 150
TEXT_COLOR_PRIMARY: Final[tuple[int, int, int]] = (255, 255, 255)
TEXT_COLOR_SECONDARY: Final[tuple[int, int, int]] = (200, 200, 200)

# Animation constants
DEFAULT_ANIMATION_FPS: Final[int] = 8

# Audio constants
DEFAULT_MUSIC_VOLUME: Final[float] = 0.7
VOLUME_STEP: Final[float] = 0.1

# File paths
CONFIG_FILE: Final[str] = "config.json"
SAVE_FILE: Final[str] = "savegame.dat"

# FPS options
ALLOWED_FPS_VALUES: Final[list[int]] = [30, 60, 90, 120, 144, 165, 180, 200, 240]


@dataclass(frozen=True)
class AssetPaths:
    """Centralized asset path definitions."""
    
    # Game assets
    GAME_IMAGES: str = "assets/game/images/"
    GAME_SOUNDS: str = "assets/game/sounds/"
    GAME_LEVELS: str = "assets/game/levels/"
    GAME_DIALOGS: str = "assets/game/dialogs/"
    
    # Menu assets
    MENU_IMAGES: str = "assets/menu/images/"
    MENU_SOUNDS: str = "assets/menu/sounds/"
    
    # Story assets
    STORY_ROOT: str = "assets/story/"
    
    # Character assets
    HERO_KNIGHT: str = "assets/game/images/hero_knight/"
    
    # HUD assets
    HUD_ROOT: str = "assets/game/images/hud/"
    
    # Dialog assets
    DIALOG_SPEAKERS: str = "assets/game/images/dialogs/speakers/"


@dataclass(frozen=True)
class PlayerConstants:
    """Player-specific constants."""
    
    MAX_HEALTH: int = 3
    MAX_MANA: int = 100
    MAX_HEARTS_DISPLAY: int = 3
    SPRITE_SIZE: tuple[int, int] = (64, 64)
    BLOCK_DAMAGE_REDUCTION: float = 0.5
    
    # Animation frame rates
    ANIMATION_FPS = {
        "idle": 7,
        "walk": 8,
        "run": 8,
        "jump": 5,
        "attack_1": 6,
        "attack_2": 5,
        "heavy_attack": 6,
        "defend": 1,
        "hurt": 4,
        "death": 12,
    }


@dataclass(frozen=True)
class UIConstants:
    """UI-specific constants."""
    
    # Font sizes
    FONT_SIZE_LARGE: int = 60
    FONT_SIZE_MEDIUM: int = 48
    FONT_SIZE_SMALL: int = 36
    FONT_SIZE_HUD: int = 24
    
    # HUD dimensions
    HUD_WIDTH: int = 380
    HUD_HEIGHT: int = 150
    HUD_PADDING: int = 50
    PORTRAIT_SIZE: tuple[int, int] = (64, 64)
    HEART_SIZE: tuple[int, int] = (24, 24)
    ICON_SIZE: tuple[int, int] = (24, 24)
    
    # Dialog dimensions
    PORTRAIT_SIZE_DIALOG: tuple[int, int] = (160, 160)
    NAME_BOX_WIDTH: int = 280
    NAME_BOX_HEIGHT: int = 50
    
    # Menu
    MENU_ITEM_SPACING: int = 20
    MENU_FADE_DURATION_MS: int = 1000
    
    # Settings
    SETTINGS_ITEM_SPACING: int = 15