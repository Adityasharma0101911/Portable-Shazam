import traceback
try:
    from src.ui.app import PortableShazamApp
    app = PortableShazamApp()
except Exception as e:
    traceback.print_exc()
