import os
import io
import json
import time
import hashlib
import threading
import webbrowser
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template
from PIL import Image
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ml_analyzer import analyzer

# Try importing rawpy for CR3 raw files support
try:
    import rawpy
    HAS_RAWPY = True
except ImportError:
    HAS_RAWPY = False
    print("Warning: 'rawpy' is not installed. CR3/RAW conversion will not be available.")

app = Flask(__name__, static_folder='static', template_folder='templates')

# Project configuration storage
WORKSPACE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = WORKSPACE_DIR / 'config.json'
CACHE_DIR = WORKSPACE_DIR / '.preview_cache'
CACHE_DIR.mkdir(exist_ok=True)

# Default configuration
config = {
    'target_directory': '',
    'mode': 'scan'  # 'scan' or 'hotfolder'
}

# In-memory hot folder events list
detected_files = []
detected_files_lock = threading.Lock()

# Global watchdog observer
observer = None
observer_thread_path = ""

# Load config if it exists
if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
            config.update(saved_config)
    except Exception as e:
        print(f"Error loading config: {e}")


def save_config():
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")


def wait_for_file_ready(filepath, timeout=15.0):
    """Wait for file write to stabilize and make sure it can be opened."""
    start_time = time.time()
    last_size = -1
    while time.time() - start_time < timeout:
        try:
            if not os.path.exists(filepath):
                time.sleep(0.2)
                continue
            # Try opening the file to see if it is locked
            with open(filepath, 'rb') as f:
                pass
            
            # Check size stability
            current_size = os.path.getsize(filepath)
            if current_size == last_size and current_size > 0:
                return True
            last_size = current_size
        except OSError:
            pass
        time.sleep(0.5)
    return False


class HotFolderHandler(FileSystemEventHandler):
    def __init__(self, target_dir):
        super().__init__()
        self.target_dir = Path(target_dir)

    def on_created(self, event):
        if event.is_directory:
            return
        
        filepath = Path(event.src_path)
        suffix = filepath.suffix.lower()
        if suffix in ['.jpg', '.jpeg', '.cr3']:
            # Wait for file copy to finish
            if wait_for_file_ready(filepath):
                try:
                    rel_path = filepath.relative_to(self.target_dir).as_posix()
                except ValueError:
                    rel_path = filepath.name  # Fallback to just name if not subpath
                
                with detected_files_lock:
                    event_id = len(detected_files) + 1
                    detected_files.append({
                        'id': event_id,
                        'name': filepath.name,
                        'path': rel_path,
                        'timestamp': time.time()
                    })
                print(f"Hot Folder: New image detected: {rel_path}")


def start_watcher(path):
    global observer, observer_thread_path
    stop_watcher()
    
    if not path or not os.path.isdir(path):
        return

    try:
        observer = Observer()
        handler = HotFolderHandler(path)
        observer.schedule(handler, path, recursive=False)
        observer.start()
        observer_thread_path = path
        print(f"Started monitoring folder: {path}")
    except Exception as e:
        print(f"Error starting watchdog observer: {e}")


def stop_watcher():
    global observer, observer_thread_path
    if observer:
        try:
            observer.stop()
            observer.join()
        except Exception as e:
            print(f"Error stopping watchdog observer: {e}")
        observer = None
        observer_thread_path = ""
        print("Stopped folder monitoring")


# Initialize watcher if target directory is set and mode is hotfolder
if config['target_directory'] and config['mode'] == 'hotfolder':
    start_watcher(config['target_directory'])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    global config
    if request.method == 'GET':
        return jsonify({
            'target_directory': config['target_directory'],
            'mode': config['mode'],
            'has_rawpy': HAS_RAWPY,
            'has_ml': analyzer.enabled
        })
    else:
        data = request.json or {}
        target_dir = data.get('target_directory', '').strip()
        mode = data.get('mode', 'scan')
        
        # Standardize path slashes for Windows
        if target_dir:
            target_dir = str(Path(target_dir).resolve())
            if not os.path.isdir(target_dir):
                return jsonify({'error': 'Directory does not exist'}), 400
        
        config['target_directory'] = target_dir
        config['mode'] = mode
        save_config()
        
        # Handle watcher start/stop
        if mode == 'hotfolder' and target_dir:
            if observer_thread_path != target_dir:
                start_watcher(target_dir)
        else:
            stop_watcher()
            
        return jsonify({'success': True, 'config': config})


@app.route('/api/images', methods=['GET'])
def api_images():
    target_dir = config['target_directory']
    if not target_dir or not os.path.isdir(target_dir):
        return jsonify([])
    
    images = []
    supported_extensions = {'.jpg', '.jpeg', '.cr3'}
    
    try:
        for entry in os.scandir(target_dir):
            if entry.is_file():
                path = Path(entry.path)
                suffix = path.suffix.lower()
                if suffix in supported_extensions:
                    # Check if sidecar JSON exists
                    sidecar = path.with_suffix('.json')
                    annotated = sidecar.exists()
                    
                    images.append({
                        'name': path.name,
                        'path': path.name,  # simple relative path for now
                        'annotated': annotated,
                        'type': suffix[1:]  # e.g., 'jpg', 'cr3'
                    })
                    
        # Sort files by name
        images.sort(key=lambda x: x['name'].lower())
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    return jsonify(images)


def get_preview_cache_path(full_path):
    """Generate a unique cache path for a RAW file preview based on path and mtime."""
    mtime = os.path.getmtime(full_path)
    # Create a unique hash
    hasher = hashlib.md5()
    hasher.update(str(full_path).encode('utf-8'))
    hasher.update(str(mtime).encode('utf-8'))
    file_hash = hasher.hexdigest()
    return CACHE_DIR / f"{file_hash}.jpg"


@app.route('/api/image', methods=['GET'])
def api_image():
    rel_path = request.args.get('path', '')
    target_dir = config['target_directory']
    if not target_dir or not rel_path:
        return jsonify({'error': 'Missing parameters'}), 400
        
    full_path = Path(target_dir) / rel_path
    if not full_path.exists() or not full_path.is_file():
        return jsonify({'error': 'File not found'}), 404
        
    suffix = full_path.suffix.lower()
    
    # Check if file is JPEG
    if suffix in ['.jpg', '.jpeg']:
        return send_file(str(full_path), mimetype='image/jpeg')
        
    # Handle CR3 / RAW files
    if suffix == '.cr3':
        if not HAS_RAWPY:
            return jsonify({'error': 'rawpy is not installed on this server to read CR3 files.'}), 500
            
        cache_path = get_preview_cache_path(full_path)
        if cache_path.exists():
            return send_file(str(cache_path), mimetype='image/jpeg')
            
        # Extract preview or render
        try:
            with rawpy.imread(str(full_path)) as raw:
                # Try extracting embedded thumbnail first (fastest)
                try:
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        # Save thumbnail to cache for future requests
                        with open(cache_path, 'wb') as cf:
                            cf.write(thumb.data)
                        return send_file(io.BytesIO(thumb.data), mimetype='image/jpeg')
                except Exception as thumb_err:
                    print(f"Could not extract embedded thumb: {thumb_err}")
                
                # Fallback to raw processing (demosaicing)
                # We use half_size=True to make it load much faster for previews
                rgb = raw.postprocess(use_camera_wb=True, half_size=True)
                img = Image.fromarray(rgb)
                
                # Save to cache
                img.save(cache_path, 'JPEG', quality=85)
                
                img_io = io.BytesIO()
                img.save(img_io, 'JPEG', quality=85)
                img_io.seek(0)
                return send_file(img_io, mimetype='image/jpeg')
        except Exception as e:
            return jsonify({'error': f"Failed to decode RAW file: {str(e)}"}), 500
            
    return jsonify({'error': 'Unsupported file type'}), 400


@app.route('/api/annotation', methods=['GET', 'POST'])
def api_annotation():
    rel_path = request.args.get('path', '')
    target_dir = config['target_directory']
    if not target_dir or not rel_path:
        return jsonify({'error': 'Missing parameters'}), 400
        
    image_path = Path(target_dir) / rel_path
    sidecar_path = image_path.with_suffix('.json')
    
    if request.method == 'GET':
        if sidecar_path.exists():
            try:
                with open(sidecar_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data.setdefault('ai_features', [])
                return jsonify(data)
            except Exception as e:
                return jsonify({'error': f"Failed to read sidecar: {str(e)}"}), 500
        else:
            # Return empty skeleton
            return jsonify({
                'subject': '',
                'date': '',
                'location': '',
                'description': '',
                'tags': [],
                'custom': {},
                'ai_features': []
            })
    else:
        # Save sidecar metadata
        data = request.json or {}
        
        # Clean data structures
        metadata = {
            'subject': data.get('subject', '').strip(),
            'date': data.get('date', '').strip(),
            'location': data.get('location', '').strip(),
            'description': data.get('description', '').strip(),
            'tags': [t.strip() for t in data.get('tags', []) if t.strip()],
            'custom': data.get('custom', {}),
            'ai_features': data.get('ai_features', []),
            'annotated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        
        try:
            with open(sidecar_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': f"Failed to save sidecar: {str(e)}"}), 500


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    rel_path = request.args.get('path', '')
    target_dir = config['target_directory']
    if not target_dir or not rel_path:
        return jsonify({'error': 'Missing parameters'}), 400
        
    full_path = Path(target_dir) / rel_path
    if not full_path.exists() or not full_path.is_file():
        return jsonify({'error': 'File not found'}), 404
        
    if not analyzer.enabled:
        return jsonify({'error': 'ML analyzer is not enabled. Please install PyTorch and Torchvision.'}), 400
        
    suffix = full_path.suffix.lower()
    
    try:
        if suffix in ['.jpg', '.jpeg']:
            features = analyzer.analyze(str(full_path))
        elif suffix == '.cr3':
            if not HAS_RAWPY:
                return jsonify({'error': 'rawpy is not installed to read CR3 files.'}), 500
            
            cache_path = get_preview_cache_path(full_path)
            if cache_path.exists():
                features = analyzer.analyze(str(cache_path))
            else:
                # Extract preview or render to PIL and analyze
                with rawpy.imread(str(full_path)) as raw:
                    try:
                        thumb = raw.extract_thumb()
                        if thumb.format == rawpy.ThumbFormat.JPEG:
                            features = analyzer.analyze(thumb.data)
                        else:
                            raise ValueError("Thumbnail not JPEG")
                    except Exception:
                        # Fallback to render
                        rgb = raw.postprocess(use_camera_wb=True, half_size=True)
                        img = Image.fromarray(rgb)
                        features = analyzer.analyze(img)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
            
        return jsonify({'success': True, 'features': features})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/hotfolder/events', methods=['GET'])
def api_hotfolder_events():
    since = int(request.args.get('since', 0))
    
    # Long polling: wait up to 5 seconds if there are no new events
    for _ in range(50):
        with detected_files_lock:
            events = [e for e in detected_files if e['id'] > since]
        if events:
            return jsonify(events)
        time.sleep(0.1)
        
    return jsonify([])


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == '__main__':
    # Start browser auto-opener thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run the server
    # Running debug=False by default to avoid reload loops causing extra browser tabs
    app.run(host='127.0.0.1', port=5000, debug=False)
