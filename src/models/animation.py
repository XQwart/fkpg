"""Animation system for sprite animations."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import pygame as pg

from src.core.interfaces import IAnimationState
from src.core.exceptions import AnimationError
from src.core.cache_manager import get_cache_manager


class Animation(IAnimationState):
    """Single animation sequence with frame management."""
    
    def __init__(
        self,
        frames: List[pg.Surface],
        fps: int,
        loop: bool = True
    ) -> None:
        """
        Initialize animation sequence.
        
        Args:
            frames: List of animation frames
            fps: Frames per second for playback
            loop: Whether animation should loop
            
        Raises:
            AnimationError: If no frames provided or invalid FPS
        """
        if not frames:
            raise AnimationError("Animation must have at least one frame")
        
        if fps <= 0:
            raise AnimationError("FPS must be positive")
        
        self._frames = frames
        self._fps = fps
        self._loop = loop
        
        self._current_frame = 0
        self._elapsed_time = 0.0
        self._frame_duration = 1.0 / fps
        self._is_playing = False
        self._is_finished = False
    
    @property
    def is_finished(self) -> bool:
        """Check if non-looping animation has finished."""
        return self._is_finished
    
    @property
    def is_playing(self) -> bool:
        """Check if animation is currently playing."""
        return self._is_playing
    
    @property
    def current_frame_index(self) -> int:
        """Get current frame index."""
        return self._current_frame
    
    @property
    def frame_count(self) -> int:
        """Get total number of frames."""
        return len(self._frames)
    
    def start(self) -> None:
        """Start or restart the animation."""
        self._current_frame = 0
        self._elapsed_time = 0.0
        self._is_playing = True
        self._is_finished = False
    
    def stop(self) -> None:
        """Stop the animation."""
        self._is_playing = False
    
    def reset(self) -> None:
        """Reset animation to first frame."""
        self._current_frame = 0
        self._elapsed_time = 0.0
        self._is_finished = False
    
    def update(self, delta_time: float) -> pg.Surface:
        """
        Update animation and return current frame.
        
        Args:
            delta_time: Time elapsed since last update in seconds
            
        Returns:
            Current animation frame
        """
        if self._is_playing and not self._is_finished:
            self._elapsed_time += delta_time
            
            # Check if we need to advance frame
            while self._elapsed_time >= self._frame_duration:
                self._elapsed_time -= self._frame_duration
                self._advance_frame()
        
        return self._frames[self._current_frame]
    
    def get_frame(self, index: int) -> pg.Surface:
        """
        Get specific frame by index.
        
        Args:
            index: Frame index
            
        Returns:
            Frame surface
            
        Raises:
            AnimationError: If index out of range
        """
        if 0 <= index < len(self._frames):
            return self._frames[index]
        raise AnimationError(f"Frame index {index} out of range")
    
    def set_fps(self, fps: int) -> None:
        """
        Change animation playback speed.
        
        Args:
            fps: New frames per second
            
        Raises:
            AnimationError: If FPS is invalid
        """
        if fps <= 0:
            raise AnimationError("FPS must be positive")
        
        self._fps = fps
        self._frame_duration = 1.0 / fps
    
    def _advance_frame(self) -> None:
        """Advance to next frame in sequence."""
        self._current_frame += 1
        
        if self._current_frame >= len(self._frames):
            if self._loop:
                self._current_frame = 0
            else:
                self._current_frame = len(self._frames) - 1
                self._is_finished = True
                self._is_playing = False


class AnimationSet:
    """Collection of animations with state management."""
    
    def __init__(self, animations: Dict[any, Animation]) -> None:
        """
        Initialize animation set.
        
        Args:
            animations: Dictionary mapping states to animations
            
        Raises:
            AnimationError: If no animations provided
        """
        if not animations:
            raise AnimationError("AnimationSet must have at least one animation")
        
        self._animations = animations
        self._current_state = next(iter(animations.keys()))
        self._current_animation = animations[self._current_state]
        self._current_animation.start()
        
        # Use centralized cache manager
        self._cache_manager = get_cache_manager()
    
    @property
    def current_state(self) -> any:
        """Get current animation state."""
        return self._current_state
    
    @property
    def current_animation(self) -> Animation:
        """Get current animation object."""
        return self._current_animation
    
    def set_state(self, state: any) -> None:
        """
        Change to a different animation state.
        
        Args:
            state: New state to transition to
            
        Raises:
            AnimationError: If state not found
        """
        if state not in self._animations:
            raise AnimationError(f"Unknown animation state: {state}")
        
        if state != self._current_state:
            # Stop current animation
            self._current_animation.stop()
            
            # Switch to new animation
            self._current_state = state
            self._current_animation = self._animations[state]
            self._current_animation.start()
    
    def update(self, delta_time: float) -> None:
        """Update current animation."""
        self._current_animation.update(delta_time)
    
    def get_current_frame(self, flip_x: bool = False, flip_y: bool = False) -> pg.Surface:
        """
        Get current frame with optional flipping.
        
        Args:
            flip_x: Whether to flip horizontally
            flip_y: Whether to flip vertically
            
        Returns:
            Current frame surface (possibly flipped)
        """
        frame = self._current_animation.update(0)  # Get current frame without updating
        
        if not flip_x and not flip_y:
            return frame
        
        # Create cache key
        cache_key = (
            id(self),  # Unique ID for this animation set
            self._current_state,
            self._current_animation.current_frame_index,
            flip_x,
            flip_y
        )
        
        # Try to get from cache
        cached = self._cache_manager.get("animation_frames", cache_key)
        
        if cached is None:
            # Create flipped frame and cache it
            cached = pg.transform.flip(frame, flip_x, flip_y)
            self._cache_manager.put("animation_frames", cache_key, cached)
        
        return cached
    
    def is_finished(self) -> bool:
        """Check if current animation has finished."""
        return self._current_animation.is_finished
    
    def add_animation(self, state: any, animation: Animation) -> None:
        """
        Add a new animation to the set.
        
        Args:
            state: State identifier for the animation
            animation: Animation object to add
        """
        self._animations[state] = animation
    
    def remove_animation(self, state: any) -> None:
        """
        Remove an animation from the set.
        
        Args:
            state: State identifier to remove
            
        Raises:
            AnimationError: If trying to remove current state
        """
        if state == self._current_state:
            raise AnimationError("Cannot remove current animation state")
        
        if state in self._animations:
            del self._animations[state]
    
    def has_state(self, state: any) -> bool:
        """Check if animation set contains given state."""
        return state in self._animations