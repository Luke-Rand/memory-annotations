import json
import logging
from pathlib import Path
from datetime import datetime
from config import ANNOTATION_TEMPLATE

logger = logging.getLogger(__name__)


class AnnotationStorage:
    """Manages JSON sidecar files for image annotations."""
    
    def __init__(self):
        self.sidecar_extension = '.json'
        
    def get_sidecar_path(self, image_path):
        """
        Return path to sidecar JSON file.
        e.g., image.jpg -> image.json
        """
        path = Path(image_path)
        return Path(path.parent, path.stem + self.sidecar_extension)
    
    def has_annotations(self, image_path):
        """Check if a sidecar annotation file exists for the image."""
        sidecar_path = self.get_sidecar_path(image_path)
        return sidecar_path.exists()
    
    def create_annotations(self, image_path, annotations):
        """
        Create a new JSON sidecar file with annotations.
        
        Args:
            image_path: Path to the image file
            annotations: Dictionary containing annotation data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            sidecar_path = self.get_sidecar_path(image_path)
            
            # Ensure required fields are present
            if annotations.get("filename") is None:
                annotations["filename"] = Path(image_path).name
            if annotations.get("annotated_at") is None:
                annotations["annotated_at"] = datetime.now().isoformat()
            
            # Validate the annotations
            if not self.validate_annotations(annotations):
                logger.error(f"Invalid annotation data for {image_path}")
                return False
            
            # Write to JSON file
            with open(sidecar_path, 'w', encoding='utf-8') as f:
                json.dump(annotations, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created annotations for {Path(image_path).name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating annotations for {image_path}: {e}")
            return False
    
    def read_annotations(self, image_path):
        """
        Read annotations from sidecar JSON file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary of annotations or None if not found/error
        """
        try:
            sidecar_path = self.get_sidecar_path(image_path)
            
            if not sidecar_path.exists():
                logger.warning(f"No annotations found for {image_path}")
                return None
            
            with open(sidecar_path, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
            
            logger.debug(f"Read annotations for {Path(image_path).name}")
            return annotations
            
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted JSON file for {image_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading annotations for {image_path}: {e}")
            return None
    
    def update_annotations(self, image_path, updates):
        """
        Update existing annotations with new data.
        
        Args:
            image_path: Path to the image file
            updates: Dictionary containing fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read existing annotations
            existing = self.read_annotations(image_path)
            if existing is None:
                logger.warning(f"No existing annotations to update for {image_path}")
                return False
            
            # Merge updates
            existing.update(updates)
            existing["updated_at"] = datetime.now().isoformat()
            
            # Write back
            sidecar_path = self.get_sidecar_path(image_path)
            with open(sidecar_path, 'w', encoding='utf-8') as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Updated annotations for {Path(image_path).name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating annotations for {image_path}: {e}")
            return False
    
    def delete_annotations(self, image_path):
        """
        Delete the sidecar annotation file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            sidecar_path = self.get_sidecar_path(image_path)
            
            if not sidecar_path.exists():
                logger.warning(f"No annotations to delete for {image_path}")
                return False
            
            sidecar_path.unlink()
            logger.info(f"Deleted annotations for {Path(image_path).name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting annotations for {image_path}: {e}")
            return False
    
    def validate_annotations(self, data):
        """
        Validate annotation data structure.
        
        Args:
            data: Dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, dict):
            return False
        
        # Check required fields exist (can be None/empty but should exist)
        required_fields = ["filename", "annotated_at"]
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate types for optional fields
        if "people" in data and not isinstance(data["people"], list):
            return False
        if "categories" in data and not isinstance(data["categories"], list):
            return False
        
        return True
    
    def list_unannotated_images(self, directory):
        """
        List all image files in directory that don't have annotations.
        
        Args:
            directory: Path to directory to scan
            
        Returns:
            List of Path objects for unannotated images
        """
        from utils import is_image_file
        
        unannotated = []
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return unannotated
        
        for file_path in dir_path.iterdir():
            if file_path.is_file() and is_image_file(file_path):
                if not self.has_annotations(file_path):
                    unannotated.append(file_path)
        
        logger.info(f"Found {len(unannotated)} unannotated images in {directory}")
        return sorted(unannotated, key=lambda x: x.stat().st_mtime, reverse=True)
        