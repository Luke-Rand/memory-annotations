"""
Main entry point for the Image Annotator application.
"""

import sys
import os
import logging
from pathlib import Path

# Add the parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_CONFIG
from utils import setup_logging, is_image_file
from storage import AnnotationStorage
from prompts import AnnotationPrompt
from watcher import DirectoryWatcher


def print_banner():
    """Print the application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   📷  IMAGE ANNOTATOR                                     ║
    ║   Monitor your directory and annotate new photos          ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def scan_unannotated(storage, directory, prompt):
    """
    Scan directory for unannotated images and offer to annotate them.
    
    Args:
        storage: AnnotationStorage instance
        directory: Path to scan
        prompt: AnnotationPrompt instance
    """
    print(f"\n🔍 Scanning for unannotated images in: {directory}")
    print("─" * 60)
    
    unannotated = storage.list_unannotated_images(directory)
    
    if not unannotated:
        print("  ✅ No unannotated images found!")
        return
    
    print(f"\n  Found {len(unannotated)} unannotated image(s):\\n")
    for i, img_path in enumerate(unannotated, 1):
        print(f"    {i}. {img_path.name}")
    
    print(f"\\n  Total: {len(unannotated)} image(s) to annotate")
    
    # Offer to annotate each one
    print("\\n  Would you like to annotate these images? (y/n)")
    response = input("  > ").strip().lower()
    
    if response in ('y', 'yes'):
        for img_path in unannotated:
            print(f"\\n  Processing: {img_path.name}")
            prompt.annotate_image(img_path)
            # Small delay to allow file system to settle
            import time
            time.sleep(0.5)
    else:
        print("  Skipping annotation.")


def run_watcher_mode(storage, prompt, config):
    """
    Run in watcher mode, monitoring directory for new images.
    
    Args:
        storage: AnnotationStorage instance
        prompt: AnnotationPrompt instance
        config: Configuration dictionary
    """
    watch_dir = config.get("watch_directory", ".")
    
    def on_new_image(filepath):
        """Callback when a new image is detected."""
        print(f"\\n  📸 New image ready for annotation: {Path(filepath).name}")
        prompt.annotate_image(filepath)
    
    print(f"\\n👁️  Starting watcher mode...")
    print(f"  Watching: {watch_dir}")
    print(f"  Press Ctrl+C to stop")
    print("─" * 60)
    
    watcher = DirectoryWatcher(
        watch_dir=watch_dir,
        callback=on_new_image,
        config=config
    )
    watcher.start()


def main():
    """Main entry point."""
    # Set up logging
    setup_logging(level=logging.INFO)
    
    # Print banner
    print_banner()
    
    # Initialize components
    storage = AnnotationStorage(DEFAULT_CONFIG)
    prompt = AnnotationPrompt(storage)
    
    # Get watch directory from config or argument
    watch_dir = DEFAULT_CONFIG.get("watch_directory", ".")
    
    if len(sys.argv) > 1:
        # If argument provided, use it as watch directory
        watch_dir = sys.argv[1]
    
    watch_path = Path(watch_dir)
    
    if not watch_path.exists():
        print(f"\\n❌ Error: Directory does not exist: {watch_dir}")
        sys.exit(1)
    
    if not watch_path.is_dir():
        print(f"\\n❌ Error: Path is not a directory: {watch_dir}")
        sys.exit(1)
    
    print(f"\\n📁 Target directory: {watch_dir}")
    
    # Scan for existing unannotated images
    scan_unannotated(storage, watch_dir, prompt)
    
    # Enter watcher mode
    print("\\n🔄 Entering watcher mode...")
    run_watcher_mode(storage, prompt, DEFAULT_CONFIG)


if __name__ == "__main__":
    main()
    