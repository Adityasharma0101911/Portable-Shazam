"""
Audio Capture Module for Portable Shazam
Handles Windows WASAPI loopback audio capture
"""
import io
import wave
import numpy as np
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class AudioSource:
    """Represents an audio source"""
    name: str
    process_id: int
    volume: float = 1.0
    is_muted: bool = False


class AudioCaptureError(Exception):
    """Custom exception for audio capture errors"""
    pass


class AudioCapture:
    """
    Handles audio capture from Windows system audio using WASAPI loopback.
    """
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._is_recording = False
        self._recorded_data = []
        self._level_callback: Optional[Callable[[float], None]] = None
        self._current_level = 0.0
        self._selected_device_name: Optional[str] = None
    
    def set_selected_device(self, device_name: str):
        """Set which device to capture from"""
        self._selected_device_name = device_name
        print(f"Selected device: {device_name}")
    
    def get_audio_sources(self) -> list[AudioSource]:
        """Get list of audio output devices"""
        sources = []
        
        try:
            import soundcard as sc
            
            # Get the user's default speaker first
            default_speaker = sc.default_speaker()
            if default_speaker:
                name = default_speaker.name
                try:
                    name = name.encode('ascii', 'replace').decode()
                except:
                    pass
                sources.append(AudioSource(
                    name=f"{name} (Default)",
                    process_id=0
                ))
            
            # Add other speakers
            for speaker in sc.all_speakers():
                if default_speaker and speaker.name == default_speaker.name:
                    continue
                name = speaker.name
                try:
                    name = name.encode('ascii', 'replace').decode()
                except:
                    pass
                sources.append(AudioSource(
                    name=name,
                    process_id=-2
                ))
                
        except Exception as e:
            sources.append(AudioSource(name="System Audio", process_id=0))
            
        return sources
    
    def capture_audio(self, duration: float, progress_callback: Optional[Callable[[float], None]] = None) -> bytes:
        """Capture system audio for the specified duration"""
        self._recorded_data = []
        self._is_recording = True
        
        try:
            return self._capture_with_loopback(duration, progress_callback)
        except Exception as e:
            raise AudioCaptureError(f"Audio capture failed: {e}")
        finally:
            self._is_recording = False
    
    def _capture_with_loopback(self, duration: float, progress_callback: Optional[Callable[[float], None]] = None) -> bytes:
        """Capture using soundcard's loopback feature"""
        import soundcard as sc
        import platform
        
        # Get all microphones including loopback devices
        all_mics = sc.all_microphones(include_loopback=True)
        
        # Find loopback device matching default speaker
        loopback = None
        default_speaker = sc.default_speaker()
        
        # Helper to find loopback
        def is_loopback(mic):
            # Check for Windows/Soundcard specific loopback attributes
            if getattr(mic, 'isloopback', False):
                return True
            # Check name for common loopback indicators
            name_lower = mic.name.lower()
            # Windows: "Loopback"
            # Linux: "Monitor"
            # macOS: "BlackHole", "Soundflower", "Loopback"
            loopback_keywords = ['loopback', 'monitor', 'blackhole', 'soundflower', 'multi-output']
            return any(keyword in name_lower for keyword in loopback_keywords)

        if default_speaker:
            print(f"Default speaker: {default_speaker.name}")
            for mic in all_mics:
                if is_loopback(mic):
                    # Try to match the loopback device to the default speaker
                    if default_speaker.name in mic.name or mic.name in default_speaker.name:
                        loopback = mic
                        break
        
        # Fallback: find any loopback
        if loopback is None:
            for mic in all_mics:
                if is_loopback(mic):
                    loopback = mic
                    break
        
        if loopback is None:
            system = platform.system()
            if system == "Darwin":  # macOS
                raise AudioCaptureError(
                    "No loopback device found on macOS.\n"
                    "Please install BlackHole: https://github.com/ExistentialAudio/BlackHole\n"
                    "Then set up a Multi-Output Device in Audio MIDI Setup."
                )
            elif system == "Linux":
                raise AudioCaptureError(
                    "No loopback device found on Linux.\n"
                    "Make sure PulseAudio or PipeWire is running with monitor devices enabled."
                )
            else:
                raise AudioCaptureError("No loopback device found")
        
        print(f"Capturing from: {loopback.name}")
        
        # Record audio
        total_frames = int(duration * self.sample_rate)
        # Smaller chunks for more responsive level meter (50ms = 20 fps)
        chunk_size = int(self.sample_rate * 0.05)
        frames_recorded = 0
        
        with loopback.recorder(samplerate=self.sample_rate, channels=self.channels) as recorder:
            while frames_recorded < total_frames and self._is_recording:
                frames_to_record = min(chunk_size, total_frames - frames_recorded)
                data = recorder.record(numframes=frames_to_record)
                self._recorded_data.append(data)
                
                if len(data) > 0:
                    # Smooth the level with a max to make it more visually appealing
                    level = float(np.abs(data).max())
                    # Smoothing: slowly decay, quickly rise
                    if level > self._current_level:
                        self._current_level = level
                    else:
                        self._current_level = self._current_level * 0.85 + level * 0.15
                    
                    if self._level_callback:
                        self._level_callback(self._current_level)
                
                frames_recorded += frames_to_record
                
                if progress_callback:
                    progress_callback(frames_recorded / total_frames)
        
        return self._convert_to_wav()
    
    def _convert_to_wav(self) -> bytes:
        """Convert recorded numpy data to WAV bytes"""
        if not self._recorded_data:
            raise AudioCaptureError("No audio data recorded")
        
        audio_data = np.concatenate(self._recorded_data, axis=0)
        
        if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
            audio_data = audio_data.mean(axis=1)
        
        audio_data = audio_data.flatten()
        
        max_amplitude = np.abs(audio_data).max()
        if max_amplitude < 0.001:
            print("Warning: Audio appears to be silent!")
        
        if max_amplitude > 0:
            audio_data = audio_data / max_amplitude * 0.9
        
        audio_data = np.clip(audio_data, -1, 1)
        audio_data = (audio_data * 32767).astype(np.int16)
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        buffer.seek(0)
        return buffer.read()
    
    def stop_recording(self):
        """Stop the current recording"""
        self._is_recording = False
    
    def set_level_callback(self, callback: Callable[[float], None]):
        """Set callback for real-time audio level updates"""
        self._level_callback = callback
    
    def get_current_level(self) -> float:
        """Get the current audio level (0-1)"""
        return self._current_level
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self._is_recording
