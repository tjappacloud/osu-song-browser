"""Playlist management for osu! Song Browser."""

import json
from pathlib import Path
from typing import List, Tuple, Optional
import random


class Playlist:
    """Represents a playlist with songs and metadata."""
    
    def __init__(self, name: str):
        """Initialize a playlist with a name.
        
        Args:
            name: The name of the playlist
        """
        self.name = name
        self.songs: List[Tuple[Path, str]] = []  # List of (path, display_title)
    
    def add_song(self, song_path: Path, display_title: str):
        """Add a song to the playlist.
        
        Args:
            song_path: Path to the audio file
            display_title: Display title for the song
        """
        song_tuple = (song_path, display_title)
        if song_tuple not in self.songs:
            self.songs.append(song_tuple)
    
    def remove_song(self, index: int):
        """Remove a song from the playlist by index.
        
        Args:
            index: Index of the song to remove
        """
        if 0 <= index < len(self.songs):
            self.songs.pop(index)
    
    def clear(self):
        """Remove all songs from the playlist."""
        self.songs.clear()
    
    def get_song(self, index: int) -> Optional[Tuple[Path, str]]:
        """Get a song by index.
        
        Args:
            index: Index of the song
            
        Returns:
            Tuple of (path, display_title) or None if index invalid
        """
        if 0 <= index < len(self.songs):
            return self.songs[index]
        return None
    
    def shuffle(self):
        """Shuffle the songs in the playlist."""
        random.shuffle(self.songs)
    
    def __len__(self):
        """Return the number of songs in the playlist."""
        return len(self.songs)
    
    def to_dict(self):
        """Convert playlist to dictionary for serialization.
        
        Returns:
            Dictionary representation of the playlist
        """
        return {
            'name': self.name,
            'songs': [{'path': str(path), 'title': title} for path, title in self.songs]
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create a playlist from a dictionary.
        
        Args:
            data: Dictionary containing playlist data
            
        Returns:
            Playlist instance
        """
        playlist = cls(data['name'])
        for song in data.get('songs', []):
            try:
                path = Path(song['path'])
                if path.exists():
                    playlist.songs.append((path, song['title']))
            except Exception:
                pass
        return playlist


class PlaylistManager:
    """Manages multiple playlists and persistence."""
    
    def __init__(self, playlists_dir: Optional[Path] = None):
        """Initialize the playlist manager.
        
        Args:
            playlists_dir: Directory to store playlist files. Defaults to user home/.osu_playlists
        """
        if playlists_dir is None:
            playlists_dir = Path.home() / '.osu_playlists'
        self.playlists_dir = playlists_dir
        self.playlists_dir.mkdir(exist_ok=True)
        
        self.playlists: List[Playlist] = []
        self.current_playlist: Optional[Playlist] = None
        self.current_index: int = 0  # Current song index in playlist
    
    def create_playlist(self, name: str) -> Playlist:
        """Create a new playlist.
        
        Args:
            name: Name for the new playlist
            
        Returns:
            The newly created playlist
        """
        playlist = Playlist(name)
        self.playlists.append(playlist)
        self.current_playlist = playlist
        return playlist
    
    def delete_playlist(self, playlist: Playlist):
        """Delete a playlist.
        
        Args:
            playlist: The playlist to delete
        """
        if playlist in self.playlists:
            self.playlists.remove(playlist)
            # Delete the file if it exists
            file_path = self.playlists_dir / f"{playlist.name}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass
            if self.current_playlist == playlist:
                self.current_playlist = None
                self.current_index = 0
    
    def save_playlist(self, playlist: Playlist):
        """Save a playlist to disk.
        
        Args:
            playlist: The playlist to save
        """
        file_path = self.playlists_dir / f"{playlist.name}.json"
        try:
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(playlist.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Failed to save playlist: {e}")
    
    def load_playlist(self, name: str) -> Optional[Playlist]:
        """Load a playlist from disk.
        
        Args:
            name: Name of the playlist to load
            
        Returns:
            The loaded playlist or None if not found
        """
        file_path = self.playlists_dir / f"{name}.json"
        if not file_path.exists():
            return None
        
        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            playlist = Playlist.from_dict(data)
            # Check if playlist already exists in memory
            existing = self.get_playlist_by_name(playlist.name)
            if existing:
                # Update existing playlist
                existing.songs = playlist.songs
                return existing
            else:
                self.playlists.append(playlist)
                return playlist
        except Exception as e:
            print(f"Failed to load playlist: {e}")
            return None
    
    def load_all_playlists(self):
        """Load all playlists from the playlists directory."""
        try:
            for file_path in self.playlists_dir.glob("*.json"):
                try:
                    with file_path.open('r', encoding='utf-8') as f:
                        data = json.load(f)
                    playlist = Playlist.from_dict(data)
                    # Avoid duplicates
                    if not self.get_playlist_by_name(playlist.name):
                        self.playlists.append(playlist)
                except Exception:
                    pass
        except Exception:
            pass
    
    def get_playlist_by_name(self, name: str) -> Optional[Playlist]:
        """Get a playlist by name.
        
        Args:
            name: Name of the playlist
            
        Returns:
            The playlist or None if not found
        """
        for playlist in self.playlists:
            if playlist.name == name:
                return playlist
        return None
    
    def set_current_playlist(self, playlist: Optional[Playlist]):
        """Set the current active playlist.
        
        Args:
            playlist: The playlist to set as current
        """
        self.current_playlist = playlist
        self.current_index = 0
    
    def next_song(self) -> Optional[Tuple[Path, str]]:
        """Get the next song in the current playlist.
        
        Returns:
            Tuple of (path, display_title) or None if no playlist/songs
        """
        if not self.current_playlist or len(self.current_playlist) == 0:
            return None
        
        self.current_index = (self.current_index + 1) % len(self.current_playlist)
        return self.current_playlist.get_song(self.current_index)
    
    def previous_song(self) -> Optional[Tuple[Path, str]]:
        """Get the previous song in the current playlist.
        
        Returns:
            Tuple of (path, display_title) or None if no playlist/songs
        """
        if not self.current_playlist or len(self.current_playlist) == 0:
            return None
        
        self.current_index = (self.current_index - 1) % len(self.current_playlist)
        return self.current_playlist.get_song(self.current_index)
    
    def current_song(self) -> Optional[Tuple[Path, str]]:
        """Get the current song in the playlist.
        
        Returns:
            Tuple of (path, display_title) or None if no playlist/songs
        """
        if not self.current_playlist or len(self.current_playlist) == 0:
            return None
        
        return self.current_playlist.get_song(self.current_index)
