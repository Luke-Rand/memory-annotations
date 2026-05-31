"""
Image Annotator

Monitor a directory for new images and prompt the user to add annotations.
Annotations are stored in JSON sidecar files.
"""

import sys
import os

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from config import DEFAULT_CONFIG
from storage import AnnotationStorage
from prompts import AnnotationPrompt
from watcher import DirectoryWatcher
from utils import setup_logging


def main():
    """Main entry point."""
    setup_logging(level="INFO")
    
    storage = AnnotationStorage(DEFAULT_CONFIG)
    prompt = AnnotationPrompt(storage)
    
    watch_dir = DEFAULT_CONFIG.get("watch_directory", ".")
    
    print(f"Watching directory: {watch_dir}")
    print("Press Ctrl+C to stop.")
    
    def on_new_image(filepath):
        """Callback when a new image is detected."""
        print(f"\nNew image detected: {filepath}")
        prompt.annotate_image(filepath)
    
    watcher = DirectoryWatcher(
        watch_dir=watch_dir,
        callback=on_new_image,
        config=DEFAULT_CONFIG
    )
    
    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\nStopping...")
        watcher.stop()


if __name__ == "__main__":
    main()
    