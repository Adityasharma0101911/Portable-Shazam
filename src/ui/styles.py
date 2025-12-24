"""
Modern UI Styles for Portable Shazam
Clean, elegant design with smooth gradients
"""

# Color Palette - Deep purple/blue theme with vibrant accents
COLORS = {
    # Backgrounds
    "bg_primary": "#0f0f1a",      # Deep dark blue
    "bg_secondary": "#1a1a2e",    # Slightly lighter
    "bg_tertiary": "#252542",     # Card backgrounds
    "bg_hover": "#2d2d4a",        # Hover states
    
    # Accent colors - Vibrant purple/pink gradient feel
    "accent_primary": "#8b5cf6",   # Vibrant purple
    "accent_secondary": "#a78bfa", # Light purple
    "accent_gradient_start": "#8b5cf6",
    "accent_gradient_end": "#ec4899",   # Pink
    
    # Text
    "text_primary": "#ffffff",
    "text_secondary": "#c4b5fd",   # Light purple tint
    "text_muted": "#6b7280",
    
    # Status colors
    "success": "#10b981",          # Emerald green
    "error": "#ef4444",            # Red
    "warning": "#f59e0b",          # Amber
    "info": "#3b82f6",             # Blue
    
    # Buttons
    "button_primary": "#8b5cf6",
    "button_primary_hover": "#7c3aed",
    "button_secondary": "#374151",
    "button_secondary_hover": "#4b5563",
    
    # Audio meter
    "meter_low": "#10b981",        # Green
    "meter_mid": "#f59e0b",        # Yellow
    "meter_high": "#ef4444",       # Red
    "meter_bg": "#1f2937",
}

# Typography
FONTS = {
    "family": "Segoe UI",
    "size_xs": 11,
    "size_sm": 12,
    "size_md": 14,
    "size_lg": 18,
    "size_xl": 24,
    "size_2xl": 32,
}

# Spacing (in pixels)
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "2xl": 48,
}

# Border radius
RADIUS = {
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "2xl": 24,
    "full": 9999,
}

# Window settings
WINDOW = {
    "title": "Portable Shazam",
    "width": 500,
    "height": 800,
    "min_width": 450,
    "min_height": 700,
}

# Animation settings
ANIMATION = {
    "pulse_speed": 50,      # ms between frames
    "meter_smoothing": 0.3, # Lower = smoother
    "transition_ms": 150,
}
