# Memory Annotations

A premium desktop-assistant and local web workspace designed to speed up cataloging, tagging, and annotating scanned slide film and RAW images (such as Canon `.cr3`). 

It serves a beautiful, high-fidelity dark-mode user interface locally in the browser, saving all annotations to clean, interoperable JSON sidecar files directly next to your images.

---

## Key Features

- **Split Workspace Layout**: Easy-to-use 3-panel UI featuring directory selection, image browser (with filter search), dynamic image viewport stage, and detail metadata panel.
- **Canon RAW (`.cr3`) Support**: Handles Canon raw files directly. It extracts embedded high-resolution JPEG previews instantly, or falls back to full RAW postprocessing (demosaicing) using `rawpy`.
- **Intelligent Preview Cache**: Renders and caches RAW preview conversions in a local `.preview_cache/` directory to ensure subsequent image loads are virtually instantaneous.
- **JSON Sidecar Standard**: Saves metadata (Subject, Date, Location, Description, custom tags, and custom key-value pairs) directly next to the original files as `<image_name>.json` to ensure your data stays permanently linked to your physical scans.
- **Modes**:
  - **Folder Scan**: Step sequentially through an existing directory of files one-by-one.
  - **Hot Folder**: Monitors a folder using `watchdog`. When a new slide copy is completed, a glowing toast notification pops up. Click it to immediately jump and annotate.
- **Keyboard Shortcuts**: Designed for fast typing flows:
  - <kbd>←</kbd> and <kbd>→</kbd> Arrow keys: Navigate to the previous or next image.
  - <kbd>Ctrl</kbd> + <kbd>S</kbd>: Save annotations.
  - <kbd>Esc</kbd>: Blur current text fields to resume arrow key navigation.

---

## Getting Started

### Prerequisites

- **Python**: Python 3.8 or higher.
- **Package Manager**: `pip` (included with Python installation).

*Note: For RAW (.cr3) file decoding, the app uses `rawpy` and `numpy` (already installed in the default system environment).*

### Installation

1. Clone or download the repository into your workspace directory.
2. Install the necessary packages:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

Start the application by running the following command in your terminal:
```bash
python app.py
```
This starts the Flask server locally and automatically opens your system default browser to:
[**`http://localhost:5000/`**](http://localhost:5000/)

---

## Directory Structure

```text
memory-annotations/
├── templates/
│   └── index.html        # Glassmorphic UI Skeleton
├── static/
│   ├── css/
│   │   └── style.css     # Dark Mode Theme Stylesheet
│   └── js/
│       └── app.js        # Form Controller and Polling Logic
├── app.py                # Flask Backend & Watcher Server
├── verify_backend.py     # Automated unittest test suite
├── requirements.txt      # Python Package Dependencies
└── README.md             # Project Guide
```

---

## Running Tests

To verify that the API routes and sidecar serialization logic are operating correctly:
```bash
python verify_backend.py
```
All unit tests should complete successfully in a fraction of a second.
