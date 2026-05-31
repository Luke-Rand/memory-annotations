"""

File watcher for detecting new images in a directory.
"""

import logging
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from utils import is_image_file, format_display_path
from config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class ImageHandler(FileSystemEventHandler):
    """Handles file system events for image files."""
    
    def __init__(self, callback=None, notify_on_new_image=True):
        """
        Initialize the image handler.
        
        Args:
            callback: Function to call when a new image is detected.
                     Should accept a filepath as argument.
            notify_on_new_image: Whether to print notifications for new images
        """
        super().__init__()
        self.callback = callback
        self.notify_on_new_image = notify_on_new_image
        self.processed_files = set()  # Track processed files to avoid duplicates
        
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
            
        filepath = event.src_path
        
        # Skip if already processed
        if filepath in self.processed_files:
            return
            
        if is_image_file(filepath):
            logger.info(f"New image detected: {format_display_path(filepath)}")
            
            if self.notify_on_new_image:
                print(f"\n🔔 New image detected: {format_display_path(filepath)}")
            
            # Mark as processed
            self.processed_files.add(filepath)
            
            # Call callback if provided
            if self.callback:
                self.callback(filepath)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        filepath = event.src_path
        
        # Only care about JSON sidecar files (annotations)
        if filepath.endswith('.json'):
            logger.info(f"Annotation file modified: {format_display_path(filepath)}")
            # Optionally handle annotation updates here


class DirectoryWatcher:
    """Watches a directory for new image files."""
    
    def __init__(self, watch_dir, callback=None, config=None):
        """
        Initialize the directory watcher.
        
        Args:
            watch_dir: Path to directory to watch
            callback: Function to call when a new image is detected
            config: Configuration dictionary
        """
        self.watch_dir = Path(watch_dir)
        self.callback = callback
        self.config = config or DEFAULT_CONFIG
        self.observer = None
        self.is_running = False
        
        # Validate watch directory
        if not self.watch_dir.exists():
            raise FileNotFoundError(f"Watch directory does not exist: {self.watch_dir}")
        if not self.watch_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.watch_dir}")
        
    def start(self):
        """Start watching the directory."""
        if self.is_running:
            logger.warning("Watcher is already running")
            return
        
        logger.info(f"Starting file watcher on: {self.watch_dir}")
        print(f"\n👁️  Watching directory: {self.watch_dir}")
        print("  Press Ctrl+C to stop watching...\\n")
        
        # Create event handler
        event_handler = ImageHandler(
            callback=self.callback,
            notify_on_new_image=self.config.get("notify_on_new_image", True)
        )
        
        # Set up observer
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_dir), recursive=False)
        self.observer.start()
        self.is_running = True
        
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Watcher stopped by user")
            print("\\n🛑 Stopping file watcher...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop watching the directory."""
        if self.observer and self.is_running:
            self.observer.stop()
            self.is_running = False
            self.observer.join()
            logger.info("File watcher stopped")
            print("  File watcher stopped.")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
