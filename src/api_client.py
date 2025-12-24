"""
Music Recognition API Client for Portable Shazam
Uses ShazamIO (free, unlimited) - https://github.com/shazamio/ShazamIO
"""
import asyncio
import os
import sys
import tempfile
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.song import SongMatch


class APIError(Exception):
    """Custom exception for API errors"""
    pass


class ShazamIOClient:
    """
    ShazamIO - Free, unlimited Shazam recognition
    No API key required!
    """
    
    name = "ShazamIO"
    
    def identify(self, audio_data: bytes) -> list[SongMatch]:
        """Identify songs using ShazamIO"""
        # Create new event loop for thread safety
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._identify_async(audio_data))
        finally:
            loop.close()
    
    async def _identify_async(self, audio_data: bytes) -> list[SongMatch]:
        """Async identification using ShazamIO"""
        from shazamio import Shazam
        
        shazam = Shazam()
        
        # Save to temp file
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            print(f"Recognizing audio ({len(audio_data)} bytes)...")
            result = await shazam.recognize(temp_path)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
        
        if not result or 'track' not in result:
            print("No match found")
            return []
        
        track = result['track']
        matches = []
        
        # Extract album
        album = "Unknown"
        for section in track.get('sections', []):
            if section.get('type') == 'SONG':
                for metadata in section.get('metadata', []):
                    if metadata.get('title') == 'Album':
                        album = metadata.get('text', 'Unknown')
                        break
        
        # Get cover art
        images = track.get('images', {})
        album_art = images.get('coverarthq') or images.get('coverart')
        
        # Build match
        match = SongMatch(
            title=track.get('title', 'Unknown'),
            artist=track.get('subtitle', 'Unknown'),
            album=album,
            confidence=100.0,
            album_art_url=album_art,
        )
        
        # Get streaming links
        hub = track.get('hub', {})
        for provider in hub.get('providers', []):
            provider_type = provider.get('type', '').upper()
            for action in provider.get('actions', []):
                uri = action.get('uri', '')
                if provider_type == 'SPOTIFY' or 'spotify' in uri.lower():
                    match.spotify_url = uri
        
        # YouTube search link
        search_query = f"{match.title} {match.artist}".replace(' ', '+')
        match.youtube_url = f"https://www.youtube.com/results?search_query={search_query}"
        
        matches.append(match)
        
        print(f"Found: {match.title} - {match.artist}")
        
        return matches


def create_client(**kwargs):
    """Create the ShazamIO client"""
    print("ShazamIO configured (FREE - Unlimited!)")
    return ShazamIOClient()
