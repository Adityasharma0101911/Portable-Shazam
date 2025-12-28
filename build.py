import os
import sys
import platform
import subprocess
import shutil

def run_build():
    """Run PyInstaller build based on the OS"""
    os_name = platform.system()
    print(f"Detected OS: {os_name}")
    
    # Clean previous builds
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        
    # Common PyInstaller args
    # Note: We use the .spec file for configuration
    cmd = [sys.executable, "-m", "PyInstaller", "PortableShazam.spec"]
    
    # Check if spec file exists
    if not os.path.exists("PortableShazam.spec"):
        print("Error: PortableShazam.spec not found!")
        sys.exit(1)
        
    print("Starting build...")
    try:
        subprocess.check_call(cmd)
        print("\nBuild successful!")
        
        # Post-build info
        if os_name == "Windows":
            print("Executable is in dist/PortableShazam.exe")
        elif os_name == "Darwin": # macOS
            print("App bundle is in dist/PortableShazam.app")
        elif os_name == "Linux":
            print("Executable is in dist/PortableShazam")
            
    except subprocess.CalledProcessError:
        print("\nBuild failed!")
        sys.exit(1)

if __name__ == "__main__":
    run_build()
