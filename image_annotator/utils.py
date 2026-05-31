"""
Utility functions for the Image Annotator application.
"""

import logging
from pathlib import Path

from config import SUPPORTED_EXTENSIONS


def setup_logging(level="INFO"):
    """Configure logging for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def is_image_file(filepath):
    """Check if a file has a supported image extension."""
    path = Path(filepath)
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def format_display_path(path):
    """Format a path for display, showing just the filename if it's in the watch directory."""
    path = Path(path)
    return str(path)


def generate_log_message(event_type, filepath):
    """Create a consistent log message for file events."""
    return f"{event_type}: {format_display_path(filepath)}"


def parse_people_input(input_str):
    """Parse comma-separated people input into a list."""
    if not input_str or not input_str.strip():
        return []
    people = [person.strip() for person in input_str.split(',')]
    # Filter out empty strings
    return [person for person in people if person]


def confirm_action(message="Are you sure?"):
    """Prompt user for yes/no confirmation."""
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        else:
            print("Please enter 'y' or 'n'.")
