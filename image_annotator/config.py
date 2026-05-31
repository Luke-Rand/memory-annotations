# Configuration for Image Annotator

# Supported image file extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp'}

# Default annotation template for sidecar JSON files
ANNOTATION_TEMPLATE = {
    "filename": None,
    "annotated_at": None,
    "people": [],
    "location": "",
    "date_approximate": "",
    "notes": "",
    "categories": []
}

# Application settings
DEFAULT_CONFIG = {
    "watch_directory": None,
    "notify_on_new_image": True,
    "log_level": "INFO",
    "allow_edit_existing": True
}
