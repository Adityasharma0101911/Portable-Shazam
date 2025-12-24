# Portable Shazam 🎵

A professional Windows desktop application that identifies songs playing on your computer using advanced audio recognition.

## ✨ Features

- **Instant Recognition** - Identifies music from any application (Spotify, YouTube, Games)
- **Zero Configuration** - No API keys required. Free and unlimited usage.
- **Modern UI** - Elegant dark mode interface with smooth animations and visualizers.
- **Detailed Results** - Displays album art, high-confidence matches, and song metadata.
- **Quick Links** - One-click access to Spotify and YouTube.
- **Song History** - Keeps track of your recently identified songs.

## 🚀 Installation

### Option 1: Standalone Executable (Recommended)
Download the latest `PortableShazam.exe` from the [Releases](https://github.com/Adityasharma0101911/Portable-Shazam/releases) page. No installation required.

### Option 2: Run from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/Adityasharma0101911/Portable-Shazam.git
   cd Portable-Shazam
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## 🛠️ How It Works

Portable Shazam uses **WASAPI Loopback** capture to record system audio directly from your sound card's output. It then fingerprints the audio and matches it against the Shazam database using `ShazamIO`, providing highly accurate results without needing microphone input.

## 💻 Tech Stack

- **Python 3.10**
- **CustomTkinter** - Modern UI framework
- **ShazamIO** - Reverse-engineered API client
- **SoundCard** - WASAPI audio capture
- **Pillow** - Image processing

## 👨‍💻 Author

**Aditya Sharma**
- [GitHub](https://github.com/Adityasharma0101911)
- [Portfolio](https://adityasharma0101.vercel.app)

## 📄 License

MIT License - Free to use and modify.

---
*Made for music lovers.*
