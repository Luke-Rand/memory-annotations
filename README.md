# Image Annotator

A Python application that monitors a directory for new images and prompts you to add annotations. Annotations are stored in JSON sidecar files alongside the images.

## Features

- 🔍 Automatically detects new images in a watched directory
- 📝 Interactive prompts for adding annotations (people, location, date, notes, categories)
- 💾 Stores annotations in JSON sidecar files (`.json` alongside images)
- ✏️ Edit existing annotations
- 🔎 Search and filter annotations
- 📊 Summary and statistics

## Requirements

- Python 3.7+
- watchdog (for file system monitoring)
- Pillow (optional, for image metadata)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m image_annotator

# Or with a specific directory
python -m image_annotator /path/to/photos
```

## Usage

### Basic Usage

```bash
# Watch the current directory
python -m image_annotator

# Watch a specific directory
python -m image_annotator /path/to/photos
```

### Configuration

Create a `config.json` file in the same directory as the application:

```json
{
  "watch_directory": "/path/to/photos",
  "supported_extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
  "annotation_suffix": ".json",
  "notify_on_new_image": true,
  "log_level": "INFO"
}
```

## Annotation Format

Annotations are stored as JSON files with the same name as the image plus a `.json` extension. For example, `photo.jpg` would have a sidecar file `photo.jpg.json`.

```json
{
  "filename": "photo.jpg",
  "people": ["Alice", "Bob"],
  "location": "Paris, France",
  "date_approximate": "June 2023",
  "notes": "Summer vacation",
  "categories": ["travel", "family"],
  "annotated_at": "2024-01-15T10:30:00"
}
```

## Project Structure

```
image_annotator/
├── __init__.py          # Package initialization
├── __main__.py          # Entry point
├── main.py              # Main application logic
├── config.py            # Configuration management
├── storage.py           # Annotation storage operations
├── prompts.py           # User interaction prompts
├── watcher.py           # File system watcher
├── utils.py             # Utility functions
└── __pycache__/         # Python cache
requirements.txt         # Dependencies
README.md               # This file
```

## Development

### Running Tests

```bash
python -m pytest
```

### Code Style

This project follows PEP 8 style guidelines.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

