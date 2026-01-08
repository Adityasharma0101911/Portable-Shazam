"""
Portable Shazam - Music Recognition App
========================================
Identify any song playing on your computer!
Uses ShazamIO - FREE unlimited song recognition!

Usage:
    python main.py
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main entry point"""
    print("Portable Shazam")
    print("=" * 40)
    
    # Check for dependencies
    missing_deps = []
    
    try:
        import PySide6
    except ImportError:
        missing_deps.append("PySide6")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import shazamio
    except ImportError:
        missing_deps.append("shazamio")
    
    try:
        import soundcard
    except ImportError:
        missing_deps.append("soundcard")
    
    if missing_deps:
        print("Missing dependencies!")
        print(f"Run: pip install {' '.join(missing_deps)}")
        sys.exit(1)
    
    print("All dependencies OK")
    print("Using ShazamIO (FREE - Unlimited!)")
    print("=" * 40)
    print("Launching modern UI...")
    
    from src.ui.app_pyside import run_app
    run_app()


if __name__ == "__main__":
    main()
