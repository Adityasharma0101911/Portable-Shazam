"""
UI Components for Portable Shazam
With album art support and song history
"""
import customtkinter as ctk
import webbrowser
from typing import Optional, List
from PIL import Image
import requests
from io import BytesIO
import threading

from src.ui.styles import COLORS, FONTS, SPACING, RADIUS


# Global song history (stores last 10 songs)
song_history: List = []


class SectionHeader(ctk.CTkFrame):
    """Simple section header"""
    
    def __init__(self, master, title: str, icon: str = "", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.title_label = ctk.CTkLabel(
            self,
            text=f"{icon}  {title}" if icon else title,
            font=(FONTS["family"], FONTS["size_lg"], "bold"),
            text_color=COLORS["text_primary"]
        )
        self.title_label.pack(anchor="w")


class AudioLevelMeter(ctk.CTkFrame):
    """Simple audio level meter"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", height=40, **kwargs)
        
        self.progress = ctk.CTkProgressBar(
            self,
            width=300,
            height=12,
            progress_color=COLORS["meter_low"],
            fg_color=COLORS["meter_bg"],
            corner_radius=6
        )
        self.progress.pack(pady=(SPACING["xs"], 0))
        self.progress.set(0)
        
        self.level_label = ctk.CTkLabel(
            self,
            text="Audio Level",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_muted"]
        )
        self.level_label.pack()
    
    def set_level(self, level: float):
        level = min(1.0, max(0.0, level))
        
        if level < 0.5:
            color = COLORS["meter_low"]
        elif level < 0.75:
            color = COLORS["meter_mid"]
        else:
            color = COLORS["meter_high"]
        
        self.progress.configure(progress_color=color)
        self.progress.set(level)
        self.level_label.configure(text=f"Audio Level: {int(level * 100)}%")
    
    def reset(self):
        self.progress.set(0)
        self.progress.configure(progress_color=COLORS["meter_low"])
        self.level_label.configure(text="Audio Level")


class PulsingButton(ctk.CTkButton):
    """Button with pulse animation"""
    
    def __init__(self, master, **kwargs):
        self._base_color = kwargs.get('fg_color', COLORS["accent_primary"])
        self._hover_color = kwargs.get('hover_color', COLORS["accent_secondary"])
        super().__init__(master, **kwargs)
        self._is_pulsing = False
    
    def start_pulse(self):
        self._is_pulsing = True
        self._pulse()
    
    def stop_pulse(self):
        self._is_pulsing = False
        self.configure(fg_color=self._base_color)
    
    def _pulse(self):
        if not self._is_pulsing:
            return
        import math, time
        brightness = 0.7 + 0.3 * math.sin(time.time() * 4)
        self.configure(fg_color=self._base_color if brightness > 0.85 else self._hover_color)
        self.after(50, self._pulse)


class StatusIndicator(ctk.CTkFrame):
    """Status indicator"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack()
        
        self.dot = ctk.CTkLabel(
            self.status_frame,
            text="●",
            font=(FONTS["family"], 12),
            text_color=COLORS["text_muted"]
        )
        self.dot.pack(side="left", padx=(0, SPACING["xs"]))
        
        self.label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            font=(FONTS["family"], FONTS["size_md"]),
            text_color=COLORS["text_muted"]
        )
        self.label.pack(side="left")
    
    def set_status(self, text: str, status_type: str = "idle"):
        colors = {
            "idle": COLORS["text_muted"],
            "listening": COLORS["accent_primary"],
            "processing": COLORS["warning"],
            "success": COLORS["success"],
            "error": COLORS["error"]
        }
        color = colors.get(status_type, COLORS["text_muted"])
        self.dot.configure(text_color=color)
        self.label.configure(text=text, text_color=color)


class SongResultCard(ctk.CTkFrame):
    """Song result card with album art"""
    
    def __init__(self, master, song, rank: int = 1, **kwargs):
        super().__init__(
            master,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=RADIUS["lg"],
            **kwargs
        )
        
        self.song = song
        
        # Add to history
        self._add_to_history(song)
        
        # Main horizontal layout
        main_row = ctk.CTkFrame(self, fg_color="transparent")
        main_row.pack(fill="x", padx=SPACING["md"], pady=SPACING["md"])
        
        # Album art placeholder (will be loaded async)
        self.album_art_label = ctk.CTkLabel(
            main_row,
            text="🎵",
            font=(FONTS["family"], 32),
            width=70,
            height=70,
            fg_color=COLORS["bg_secondary"],
            corner_radius=RADIUS["md"]
        )
        self.album_art_label.pack(side="left", padx=(0, SPACING["md"]))
        
        # Load album art in background
        if song.album_art_url:
            threading.Thread(
                target=self._load_album_art,
                args=(song.album_art_url,),
                daemon=True
            ).start()
        
        # Song info
        info_frame = ctk.CTkFrame(main_row, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        
        # Rank and title row
        title_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        title_row.pack(fill="x")
        
        rank_label = ctk.CTkLabel(
            title_row,
            text=f"#{rank}",
            font=(FONTS["family"], FONTS["size_sm"], "bold"),
            text_color=COLORS["accent_primary"]
        )
        rank_label.pack(side="left", padx=(0, SPACING["sm"]))
        
        title_label = ctk.CTkLabel(
            title_row,
            text=song.title,
            font=(FONTS["family"], FONTS["size_md"], "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)
        
        # Artist
        artist_label = ctk.CTkLabel(
            info_frame,
            text=f"🎤 {song.artist}",
            font=(FONTS["family"], FONTS["size_sm"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        artist_label.pack(anchor="w")
        
        # Album
        if song.album and song.album != "Unknown":
            album_label = ctk.CTkLabel(
                info_frame,
                text=f"💿 {song.album}",
                font=(FONTS["family"], FONTS["size_xs"]),
                text_color=COLORS["text_muted"],
                anchor="w"
            )
            album_label.pack(anchor="w")
        
        # Confidence with visual bar
        conf_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        conf_frame.pack(fill="x", pady=(SPACING["xs"], 0))
        
        conf_bar = ctk.CTkProgressBar(
            conf_frame,
            width=80,
            height=8,
            progress_color=COLORS["success"],
            fg_color=COLORS["bg_secondary"],
            corner_radius=4
        )
        conf_bar.pack(side="left")
        conf_bar.set(song.confidence / 100)
        
        conf_label = ctk.CTkLabel(
            conf_frame,
            text=f"{song.confidence:.0f}% match",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["success"]
        )
        conf_label.pack(side="left", padx=(SPACING["sm"], 0))
        
        # Buttons row
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=SPACING["md"], pady=(0, SPACING["md"]))
        
        if song.youtube_url:
            yt_btn = ctk.CTkButton(
                buttons,
                text="▶ YouTube",
                width=95,
                height=30,
                font=(FONTS["family"], FONTS["size_sm"]),
                fg_color="#ff0000",
                hover_color="#cc0000",
                corner_radius=RADIUS["md"],
                command=lambda: webbrowser.open(song.youtube_url)
            )
            yt_btn.pack(side="left", padx=(0, SPACING["sm"]))
        
        if song.spotify_url:
            sp_btn = ctk.CTkButton(
                buttons,
                text="♪ Spotify",
                width=95,
                height=30,
                font=(FONTS["family"], FONTS["size_sm"]),
                fg_color="#1db954",
                hover_color="#1aa34a",
                corner_radius=RADIUS["md"],
                command=lambda: webbrowser.open(song.spotify_url)
            )
            sp_btn.pack(side="left")
    
    def _load_album_art(self, url: str):
        """Load album art from URL in background"""
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                img_data = BytesIO(response.content)
                pil_image = Image.open(img_data)
                pil_image = pil_image.resize((70, 70), Image.Resampling.LANCZOS)
                
                # Convert to CTkImage
                ctk_image = ctk.CTkImage(
                    light_image=pil_image,
                    dark_image=pil_image,
                    size=(70, 70)
                )
                
                # Update on main thread
                self.after(0, lambda: self._set_album_art(ctk_image))
        except Exception as e:
            print(f"Failed to load album art: {e}")
    
    def _set_album_art(self, image):
        """Set album art image (called from main thread)"""
        self.album_art_label.configure(image=image, text="")
    
    def _add_to_history(self, song):
        """Add song to global history"""
        global song_history
        # Avoid duplicates
        for s in song_history:
            if s.title == song.title and s.artist == song.artist:
                return
        
        song_history.insert(0, song)
        if len(song_history) > 10:
            song_history.pop()


class HistoryCard(ctk.CTkFrame):
    """Small history item card"""
    
    def __init__(self, master, song, index: int, **kwargs):
        super().__init__(
            master,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=RADIUS["md"],
            height=40,
            **kwargs
        )
        
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=SPACING["sm"], pady=SPACING["xs"])
        
        # Index
        idx_label = ctk.CTkLabel(
            row,
            text=f"{index}.",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_muted"],
            width=20
        )
        idx_label.pack(side="left")
        
        # Song info
        info = ctk.CTkLabel(
            row,
            text=f"{song.title} - {song.artist}",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        info.pack(side="left", fill="x", expand=True)
        
        # Confidence
        conf = ctk.CTkLabel(
            row,
            text=f"{song.confidence:.0f}%",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=COLORS["success"]
        )
        conf.pack(side="right")


class ScrollableResultsFrame(ctk.CTkScrollableFrame):
    """Scrollable results with history"""
    
    def __init__(self, master, **kwargs):
        fg_color = kwargs.pop('fg_color', COLORS["bg_secondary"])
        super().__init__(
            master,
            fg_color=fg_color,
            corner_radius=RADIUS["lg"],
            scrollbar_button_color=COLORS["accent_primary"],
            scrollbar_button_hover_color=COLORS["accent_secondary"],
            **kwargs
        )
        self.result_cards = []
    
    def clear_results(self):
        for card in self.result_cards:
            card.destroy()
        self.result_cards = []
    
    def add_result(self, song, rank: int):
        """Add a song result card"""
        card = SongResultCard(self, song, rank)
        card.pack(fill="x", pady=SPACING["xs"], padx=SPACING["xs"])
        self.result_cards.append(card)
    
    def show_history(self):
        """Show song history section"""
        global song_history
        
        if not song_history:
            return
        
        # Add separator
        sep = ctk.CTkFrame(self, fg_color=COLORS["bg_hover"], height=1)
        sep.pack(fill="x", pady=SPACING["md"], padx=SPACING["sm"])
        self.result_cards.append(sep)
        
        # History header
        header = ctk.CTkLabel(
            self,
            text="� Recent Songs (Top 10)",
            font=(FONTS["family"], FONTS["size_sm"], "bold"),
            text_color=COLORS["text_secondary"]
        )
        header.pack(anchor="w", padx=SPACING["sm"])
        self.result_cards.append(header)
        
        # History items
        for i, song in enumerate(song_history[:10], 1):
            card = HistoryCard(self, song, i)
            card.pack(fill="x", pady=2, padx=SPACING["xs"])
            self.result_cards.append(card)
    
    def show_no_results(self):
        self.clear_results()
        
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, pady=SPACING["lg"])
        
        icon = ctk.CTkLabel(frame, text="🔍", font=(FONTS["family"], 40))
        icon.pack()
        
        text = ctk.CTkLabel(
            frame,
            text="No matches found",
            font=(FONTS["family"], FONTS["size_lg"]),
            text_color=COLORS["text_secondary"]
        )
        text.pack(pady=(SPACING["sm"], 0))
        
        self.result_cards.append(frame)
        
        # Show history if available
        self.show_history()
    
    def show_error(self, message: str):
        self.clear_results()
        
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, pady=SPACING["lg"])
        
        icon = ctk.CTkLabel(frame, text="⚠️", font=(FONTS["family"], 40))
        icon.pack()
        
        text = ctk.CTkLabel(
            frame,
            text="Error",
            font=(FONTS["family"], FONTS["size_lg"]),
            text_color=COLORS["error"]
        )
        text.pack(pady=(SPACING["sm"], 0))
        
        msg = ctk.CTkLabel(
            frame,
            text=message,
            font=(FONTS["family"], FONTS["size_sm"]),
            text_color=COLORS["text_muted"],
            wraplength=280
        )
        msg.pack()
        
        self.result_cards.append(frame)
