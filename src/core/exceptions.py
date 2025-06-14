"""Custom exceptions for the Fallen Knight game."""
from __future__ import annotations


class GameError(Exception):
    """Base exception for all game-related errors."""
    pass


class ResourceError(GameError):
    """Raised when a resource cannot be loaded or accessed."""
    pass


class SceneError(GameError):
    """Raised when there's an error with scene management."""
    pass


class ConfigError(GameError):
    """Raised when there's an error with configuration."""
    pass


class LevelError(GameError):
    """Raised when there's an error loading or parsing a level."""
    pass


class DialogError(GameError):
    """Raised when there's an error with dialog system."""
    pass


class AnimationError(GameError):
    """Raised when there's an error with animations."""
    pass


class EntityError(GameError):
    """Raised when there's an error with entity management."""
    pass