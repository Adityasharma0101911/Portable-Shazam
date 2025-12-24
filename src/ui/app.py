"""
Main Application Window for Portable Shazam
"""
import customtkinter as ctk
import webbrowser
import threading
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ui.styles import COLORS, FONTS, SPACING, RADIUS, WINDOW
from src.ui.components import (
    SectionHeader,
    AudioLevelMeter,
    PulsingButton,
    ScrollableResultsFrame,
    StatusIndicator
)
from src.audio_capture import AudioCapture, AudioCaptureError
from src.api_client import create_client, APIError
from src.models.song import SongMatch

# Import config
try:
    import config
except ImportError:
    config = None


class PortableShazamApp(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title(WINDOW["title"])
        self.geometry(f"{WINDOW['width']}x{WINDOW['height']}")
        self.minsize(WINDOW["min_width"], WINDOW["min_height"])
        self.configure(fg_color=COLORS["bg_primary"])
        
        # Set appearance mode
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize components
        self.audio_capture = AudioCapture()
        self.api_client = self._create_api_client()
        
        self._is_listening = False
        self._recording_thread = None
        
        # Build UI
        self._create_header()
        self._create_audio_source_section()
        self._create_listen_section()
        self._create_results_section()
        self._create_footer()
        
        # Update audio sources
        self._update_audio_sources()
    
    def _create_api_client(self):
        """Create the ShazamIO client - no config needed, it's free!"""
        return create_client()
    
    def _create_header(self):
        """Create elegant centered header"""
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=SPACING["xl"], pady=(SPACING["lg"], SPACING["md"]))
        
        # Centered title section
        self.title_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.title_frame.pack()
        
        # Large icon
        self.app_icon = ctk.CTkLabel(
            self.title_frame,
            text="🎵",
            font=(FONTS["family"], 48)
        )
        self.app_icon.pack()
        
        # App title with accent color
        self.app_title = ctk.CTkLabel(
            self.title_frame,
            text="Portable Shazam",
            font=(FONTS["family"], FONTS["size_2xl"], "bold"),
            text_color=COLORS["text_primary"]
        )
        self.app_title.pack(pady=(SPACING["xs"], 0))
        
        # Subtitle
        self.app_subtitle = ctk.CTkLabel(
            self.title_frame,
            text="Identify any song in seconds",
            font=(FONTS["family"], FONTS["size_sm"]),
            text_color=COLORS["text_secondary"]
        )
        self.app_subtitle.pack()
    
    def _create_audio_source_section(self):
        """Create audio source selection - just audio output devices"""
        self.source_section = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=RADIUS["lg"]
        )
        self.source_section.pack(fill="x", padx=SPACING["xl"], pady=(0, SPACING["lg"]))
        
        self.source_content = ctk.CTkFrame(self.source_section, fg_color="transparent")
        self.source_content.pack(fill="x", padx=SPACING["lg"], pady=SPACING["lg"])
        
        # Header
        self.source_header = SectionHeader(self.source_content, "Audio Output", "")
        self.source_header.pack(fill="x")
        
        # Description
        self.source_desc = ctk.CTkLabel(
            self.source_content,
            text="Select the audio output device you're listening on",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_muted"]
        )
        self.source_desc.pack(anchor="w", pady=(SPACING["xs"], 0))
        
        # Dropdown row
        self.source_row = ctk.CTkFrame(self.source_content, fg_color="transparent")
        self.source_row.pack(fill="x", pady=(SPACING["md"], 0))
        
        self.source_var = ctk.StringVar(value="Loading...")
        self.source_dropdown = ctk.CTkOptionMenu(
            self.source_row,
            variable=self.source_var,
            values=["Loading..."],
            width=280,
            height=40,
            font=(FONTS["family"], FONTS["size_md"]),
            fg_color=COLORS["bg_tertiary"],
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_secondary"],
            dropdown_fg_color=COLORS["bg_secondary"],
            dropdown_hover_color=COLORS["bg_hover"],
            command=self._on_source_changed
        )
        self.source_dropdown.pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(
            self.source_row,
            text="Refresh",
            width=70,
            height=40,
            font=(FONTS["family"], FONTS["size_sm"]),
            fg_color=COLORS["button_secondary"],
            hover_color=COLORS["button_secondary_hover"],
            command=self._update_audio_sources
        )
        self.refresh_btn.pack(side="left", padx=(SPACING["sm"], 0))
        
        # Status indicator
        self.active_apps_label = ctk.CTkLabel(
            self.source_content,
            text="",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_muted"]
        )
        self.active_apps_label.pack(anchor="w", pady=(SPACING["sm"], 0))
    
    def _create_listen_section(self):
        """Create the main listen section"""
        self.listen_section = ctk.CTkFrame(self, fg_color="transparent")
        self.listen_section.pack(fill="x", padx=SPACING["xl"], pady=(0, SPACING["lg"]))
        
        # Level meter
        self.level_meter = AudioLevelMeter(self.listen_section)
        self.level_meter.pack(fill="x", pady=(0, SPACING["md"]))
        
        # Listen button container (for centering)
        self.button_container = ctk.CTkFrame(self.listen_section, fg_color="transparent")
        self.button_container.pack(expand=True, pady=SPACING["md"])
        
        # Big listen button
        self.listen_button = PulsingButton(
            self.button_container,
            text="🎤  LISTEN",
            width=200,
            height=70,
            font=(FONTS["family"], FONTS["size_xl"], "bold"),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_secondary"],
            corner_radius=RADIUS["xl"],
            command=self._toggle_listening
        )
        self.listen_button.pack()
        
        # Status indicator
        self.status = StatusIndicator(self.listen_section)
        self.status.pack(pady=(SPACING["md"], 0))
        
        # Progress bar (hidden by default)
        self.progress_container = ctk.CTkFrame(self.listen_section, fg_color="transparent")
        self.progress_container.pack(fill="x", pady=(SPACING["sm"], 0))
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_container,
            width=300,
            height=6,
            progress_color=COLORS["accent_primary"]
        )
        self.progress_bar.set(0)
        # Hidden initially
    
    def _create_results_section(self):
        """Create results display section"""
        self.results_section = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=RADIUS["lg"]
        )
        self.results_section.pack(fill="both", expand=True, padx=SPACING["xl"], pady=(0, SPACING["lg"]))
        
        self.results_content = ctk.CTkFrame(self.results_section, fg_color="transparent")
        self.results_content.pack(fill="both", expand=True, padx=SPACING["lg"], pady=SPACING["lg"])
        
        # Header
        self.results_header = SectionHeader(self.results_content, "Results", "📋")
        self.results_header.pack(fill="x")
        
        # Scrollable results
        self.results_frame = ScrollableResultsFrame(
            self.results_content,
            fg_color=COLORS["bg_primary"]
        )
        self.results_frame.pack(fill="both", expand=True, pady=(SPACING["md"], 0))
        
        # Initial state
        self._show_initial_state()
    
    def _create_footer(self):
        """Create application footer with credits"""
        self.footer = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.footer.pack(fill="x", padx=SPACING["xl"], pady=(0, SPACING["md"]))
        
        # Credits container
        credits_frame = ctk.CTkFrame(self.footer, fg_color="transparent")
        credits_frame.pack(side="left")
        
        ctk.CTkLabel(
            credits_frame,
            text="Created by Aditya Sharma",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w")
        
        # Links
        links_frame = ctk.CTkFrame(credits_frame, fg_color="transparent")
        links_frame.pack(anchor="w")
        
        github_btn = ctk.CTkButton(
            links_frame,
            text="GitHub",
            font=(FONTS["family"], 11),
            width=50,
            height=20,
            fg_color="transparent",
            text_color=COLORS["accent_primary"],
            hover_color=COLORS["bg_secondary"],
            command=lambda: webbrowser.open("https://github.com/Adityasharma0101911/Portable-Shazam")
        )
        github_btn.pack(side="left", padx=(0, 5))
        
        portfolio_btn = ctk.CTkButton(
            links_frame,
            text="Portfolio",
            font=(FONTS["family"], 11),
            width=60,
            height=20,
            fg_color="transparent",
            text_color=COLORS["accent_primary"],
            hover_color=COLORS["bg_secondary"],
            command=lambda: webbrowser.open("https://adityasharma0101.vercel.app")
        )
        portfolio_btn.pack(side="left")
        
        # Version
        self.version_text = ctk.CTkLabel(
            self.footer,
            text="v1.0.0",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_muted"]
        )
        self.version_text.pack(side="right")
    
    def _show_initial_state(self):
        """Show initial state message in results"""
        self.results_frame.clear_results()
        
        initial_frame = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        initial_frame.pack(fill="both", expand=True, pady=SPACING["2xl"])
        
        icon = ctk.CTkLabel(
            initial_frame,
            text="🎧",
            font=(FONTS["family"], 64)
        )
        icon.pack()
        
        text = ctk.CTkLabel(
            initial_frame,
            text="Ready to identify music",
            font=(FONTS["family"], FONTS["size_lg"]),
            text_color=COLORS["text_secondary"]
        )
        text.pack(pady=(SPACING["md"], 0))
        
        hint = ctk.CTkLabel(
            initial_frame,
            text="Play some music and click LISTEN",
            font=(FONTS["family"], FONTS["size_sm"]),
            text_color=COLORS["text_muted"]
        )
        hint.pack()
        
        self.results_frame.result_cards.append(initial_frame)
    
    def _on_source_changed(self, selected_value: str):
        """Called when user selects a different audio output device"""
        if selected_value == "Loading...":
            return
        self.audio_capture.set_selected_device(selected_value)
        self.active_apps_label.configure(text=f"Capturing from: {selected_value}")
    
    def _get_audio_devices(self) -> list[str]:
        """Get list of audio output devices"""
        devices = []
        try:
            import soundcard as sc
            
            # Add default speaker first
            default = sc.default_speaker()
            if default:
                name = default.name
                try:
                    name = name.encode('ascii', 'replace').decode()
                except:
                    pass
                devices.append(f"{name} (Default)")
            
            # Add other speakers
            for speaker in sc.all_speakers():
                if default and speaker.name == default.name:
                    continue
                name = speaker.name
                try:
                    name = name.encode('ascii', 'replace').decode()
                except:
                    pass
                devices.append(name)
        except Exception:
            devices.append("System Audio")
        
        return devices
    
    def _update_audio_sources(self):
        """Update the audio devices dropdown"""
        devices = self._get_audio_devices()
        
        self.source_dropdown.configure(values=devices)
        
        # Set first item as selected
        if devices:
            self.source_var.set(devices[0])
            self.audio_capture.set_selected_device(devices[0])
            self.active_apps_label.configure(text=f"Capturing from: {devices[0]}")
    
    def _toggle_listening(self):
        """Toggle listening state"""
        if self._is_listening:
            self._stop_listening()
        else:
            self._start_listening()
    
    def _start_listening(self):
        """Start listening for music"""
        self._is_listening = True
        
        # Update UI
        self.listen_button.configure(text="🛑  STOP")
        self.listen_button.start_pulse()
        self.status.set_status("Listening...", "listening")
        self.progress_bar.pack(pady=(SPACING["sm"], 0))
        self.progress_bar.set(0)
        
        # Set up level callback
        self.audio_capture.set_level_callback(self._update_level)
        
        # Start recording in background
        self._recording_thread = threading.Thread(target=self._record_and_identify)
        self._recording_thread.daemon = True
        self._recording_thread.start()
    
    def _stop_listening(self):
        """Stop listening"""
        self._is_listening = False
        self.audio_capture.stop_recording()
        
        # Update UI
        self.listen_button.configure(text="🎤  LISTEN")
        self.listen_button.stop_pulse()
        self.status.set_status("Stopped", "idle")
        self.progress_bar.pack_forget()
        self.level_meter.reset()
    
    def _update_level(self, level: float):
        """Update audio level meter (called from background thread)"""
        self.after(0, lambda: self.level_meter.set_level(level))
    
    def _update_progress(self, progress: float):
        """Update progress bar (called from background thread)"""
        self.after(0, lambda: self.progress_bar.set(progress))
    
    def _record_and_identify(self):
        """Record audio and send for identification (runs in background)"""
        try:
            # Get recording duration from config
            duration = getattr(config, 'RECORDING_DURATION', 5) if config else 5
            
            # Record audio
            audio_data = self.audio_capture.capture_audio(
                duration=duration,
                progress_callback=self._update_progress
            )
            
            if not self._is_listening:
                return  # Stopped early
            
            # Update status
            self.after(0, lambda: self.status.set_status("Identifying...", "processing"))
            
            # Send to API
            results = self.api_client.identify(audio_data)
            
            # Display results
            self.after(0, lambda: self._display_results(results))
            
        except AudioCaptureError as e:
            error_msg = f"Audio capture error: {e}"
            self.after(0, lambda msg=error_msg: self._show_error(msg))
        except APIError as e:
            error_msg = f"API error: {e}"
            self.after(0, lambda msg=error_msg: self._show_error(msg))
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.after(0, lambda msg=error_msg: self._show_error(msg))
        finally:
            self.after(0, self._finish_listening)
    
    def _finish_listening(self):
        """Reset UI after listening completes"""
        self._is_listening = False
        self.listen_button.configure(text="🎤  LISTEN")
        self.listen_button.stop_pulse()
        self.progress_bar.pack_forget()
        self.level_meter.reset()
    
    def _display_results(self, results: list[SongMatch]):
        """Display song recognition results"""
        self.results_frame.clear_results()
        
        if not results:
            self.status.set_status("No matches found", "idle")
            self.results_frame.show_no_results()
            return
        
        self.status.set_status(f"Found {len(results)} match(es)", "success")
        
        for i, song in enumerate(results, 1):
            self.results_frame.add_result(song, i)
    
    def _show_error(self, message: str):
        """Display error message"""
        self.status.set_status("Error occurred", "error")
        self.results_frame.show_error(message)


def run_app():
    """Entry point to run the application"""
    app = PortableShazamApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()
