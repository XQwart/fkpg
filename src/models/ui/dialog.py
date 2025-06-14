"""Dialog system model for story and in-game conversations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

from src.core.exceptions import DialogError


@dataclass(frozen=True)
class DialogEntry:
    """Single dialog entry with all associated data."""
    
    text: str
    speaker: Optional[str] = None
    portrait: Optional[str] = None
    image: Optional[str] = None
    sound: Optional[str] = None
    
    def __post_init__(self):
        """Validate dialog entry."""
        if not self.text:
            raise DialogError("Dialog entry must have text")


class DialogSequence:
    """A sequence of dialog entries."""
    
    def __init__(self, entries: List[DialogEntry]) -> None:
        """Initialize dialog sequence."""
        if not entries:
            raise DialogError("Dialog sequence must have at least one entry")
        
        self._entries = entries
        self._current_index = 0
    
    @property
    def current_entry(self) -> DialogEntry:
        """Get current dialog entry."""
        return self._entries[self._current_index]
    
    @property
    def current_index(self) -> int:
        """Get current dialog index."""
        return self._current_index
    
    @property
    def total_entries(self) -> int:
        """Get total number of entries."""
        return len(self._entries)
    
    @property
    def is_finished(self) -> bool:
        """Check if dialog sequence has finished."""
        return self._current_index >= len(self._entries) - 1
    
    def advance(self) -> bool:
        """
        Advance to next dialog entry.
        
        Returns:
            True if advanced, False if at end
        """
        if not self.is_finished:
            self._current_index += 1
            return True
        return False
    
    def reset(self) -> None:
        """Reset dialog to beginning."""
        self._current_index = 0
    
    def skip_to_end(self) -> None:
        """Skip to last dialog entry."""
        self._current_index = len(self._entries) - 1
    
    def get_entry(self, index: int) -> DialogEntry:
        """
        Get dialog entry by index.
        
        Args:
            index: Entry index
            
        Returns:
            Dialog entry
            
        Raises:
            DialogError: If index out of range
        """
        if 0 <= index < len(self._entries):
            return self._entries[index]
        raise DialogError(f"Dialog index {index} out of range")


class DialogManager:
    """Manages loading and storing dialog sequences."""
    
    def __init__(self) -> None:
        """Initialize dialog manager."""
        self._sequences: Dict[str, DialogSequence] = {}
        self._current_sequence: Optional[DialogSequence] = None
    
    @property
    def current_sequence(self) -> Optional[DialogSequence]:
        """Get currently active dialog sequence."""
        return self._current_sequence
    
    def load_sequence_from_file(self, dialog_id: str, file_path: Path) -> DialogSequence:
        """
        Load dialog sequence from file.
        
        Args:
            dialog_id: Unique identifier for the sequence
            file_path: Path to dialog file (JSON or TXT)
            
        Returns:
            Loaded dialog sequence
            
        Raises:
            DialogError: If file cannot be loaded or parsed
        """
        if not file_path.exists():
            raise DialogError(f"Dialog file not found: {file_path}")
        
        try:
            if file_path.suffix == '.json':
                sequence = self._load_json_dialog(file_path)
            elif file_path.suffix == '.txt':
                sequence = self._load_txt_dialog(file_path)
            else:
                raise DialogError(f"Unsupported dialog format: {file_path.suffix}")
            
            self._sequences[dialog_id] = sequence
            return sequence
            
        except (IOError, json.JSONDecodeError) as e:
            raise DialogError(f"Failed to load dialog: {e}")
    
    def get_sequence(self, dialog_id: str) -> Optional[DialogSequence]:
        """Get dialog sequence by ID."""
        return self._sequences.get(dialog_id)
    
    def start_sequence(self, dialog_id: str) -> DialogSequence:
        """
        Start a dialog sequence.
        
        Args:
            dialog_id: ID of sequence to start
            
        Returns:
            Started dialog sequence
            
        Raises:
            DialogError: If sequence not found
        """
        sequence = self._sequences.get(dialog_id)
        if not sequence:
            raise DialogError(f"Dialog sequence not found: {dialog_id}")
        
        sequence.reset()
        self._current_sequence = sequence
        return sequence
    
    def end_current_sequence(self) -> None:
        """End the current dialog sequence."""
        self._current_sequence = None
    
    def clear_sequences(self) -> None:
        """Clear all loaded sequences."""
        self._sequences.clear()
        self._current_sequence = None
    
    def _load_json_dialog(self, file_path: Path) -> DialogSequence:
        """Load dialog from JSON format."""
        with file_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise DialogError("JSON dialog must be a list of entries")
        
        entries = []
        for item in data:
            if isinstance(item, dict):
                entries.append(DialogEntry(**item))
            else:
                raise DialogError("Each dialog entry must be a dictionary")
        
        return DialogSequence(entries)
    
    def _load_txt_dialog(self, file_path: Path) -> DialogSequence:
        """Load dialog from text format (pipe-separated)."""
        entries = []
        
        with file_path.open('r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                
                parts = line.split('|')
                if not parts or not parts[0]:
                    raise DialogError(f"Invalid dialog entry at line {line_num}")
                
                # Build entry from parts
                entry_data = {'text': parts[0]}
                
                # Optional fields
                if len(parts) > 1 and parts[1]:
                    entry_data['image'] = parts[1]
                if len(parts) > 2 and parts[2]:
                    entry_data['sound'] = parts[2]
                if len(parts) > 3 and parts[3]:
                    entry_data['speaker'] = parts[3]
                if len(parts) > 4 and parts[4]:
                    entry_data['portrait'] = parts[4]
                
                entries.append(DialogEntry(**entry_data))
        
        return DialogSequence(entries)


# Singleton instance
_dialog_manager = DialogManager()


def get_dialog_manager() -> DialogManager:
    """Get the global dialog manager instance."""
    return _dialog_manager