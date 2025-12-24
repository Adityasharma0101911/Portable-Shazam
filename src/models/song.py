"""
Song data model for Portable Shazam
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SongMatch:
    """Represents a matched song from the recognition API"""
    title: str
    artist: str
    album: str
    confidence: float  # 0-100 percentage
    album_art_url: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    preview_url: Optional[str] = None
    release_date: Optional[str] = None
    duration_ms: Optional[int] = None
    genres: Optional[list[str]] = None
    
    def __post_init__(self):
        """Validate confidence is within range"""
        self.confidence = max(0, min(100, self.confidence))
    
    @property
    def formatted_duration(self) -> str:
        """Return duration as MM:SS format"""
        if self.duration_ms is None:
            return "Unknown"
        seconds = self.duration_ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def get_best_link(self) -> Optional[str]:
        """Return the best available streaming link"""
        return self.spotify_url or self.apple_music_url or self.youtube_url
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "confidence": self.confidence,
            "album_art_url": self.album_art_url,
            "spotify_url": self.spotify_url,
            "apple_music_url": self.apple_music_url,
            "youtube_url": self.youtube_url,
            "preview_url": self.preview_url,
            "release_date": self.release_date,
            "duration_ms": self.duration_ms,
            "genres": self.genres
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SongMatch":
        """Create SongMatch from dictionary"""
        return cls(
            title=data.get("title", "Unknown"),
            artist=data.get("artist", "Unknown"),
            album=data.get("album", "Unknown"),
            confidence=data.get("confidence", 0),
            album_art_url=data.get("album_art_url"),
            spotify_url=data.get("spotify_url"),
            apple_music_url=data.get("apple_music_url"),
            youtube_url=data.get("youtube_url"),
            preview_url=data.get("preview_url"),
            release_date=data.get("release_date"),
            duration_ms=data.get("duration_ms"),
            genres=data.get("genres")
        )
    
    def __str__(self) -> str:
        return f"{self.title} - {self.artist} ({self.confidence:.1f}%)"
