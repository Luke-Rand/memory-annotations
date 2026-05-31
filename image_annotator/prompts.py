"""
Annotation prompt interface for user interaction.
"""

import logging
from pathlib import Path
from storage import AnnotationStorage
from utils import parse_people_input, confirm_action

logger = logging.getLogger(__name__)


class AnnotationPrompt:
    """Handles user interaction for adding annotations to images."""
    
    def __init__(self, storage):
        """
        Initialize the annotation prompt.
        
        Args:
            storage: AnnotationStorage instance for saving annotations
        """
        self.storage = storage
        
    def display_header(self, image_path):
        """Display a header with the image filename."""
        filename = Path(image_path).name
        width = 60
        print("\n" + "═" * width)
        print(f"  📷 New Image Detected: {filename}")
        print("═" * width)
        print(f"  Path: {image_path}")
        print("─" * width)
        
    def display_existing_annotations(self, annotations):
        """Display existing annotations if they exist."""
        print("\n  📝 Existing Annotations:")
        print("  " + "─" * 40)
        
        if annotations.get("people"):
            print(f"  People: {', '.join(annotations['people'])}")
        if annotations.get("location"):
            print(f"  Location: {annotations['location']}")
        if annotations.get("date_approximate"):
            print(f"  Date: {annotations['date_approximate']}")
        if annotations.get("notes"):
            print(f"  Notes: {annotations['notes']}")
        if annotations.get("categories"):
            print(f"  Categories: {', '.join(annotations['categories'])}")
        print("  " + "─" * 40)
        
    def prompt_people(self, existing=None):
        """
        Prompt user for people in the photo.
        
        Args:
            existing: Existing list of people (if editing)
            
        Returns:
            List of people names
        """
        prompt = "  Enter people in photo (comma-separated, or press Enter to skip): "
        if existing:
            prompt = f"  Enter people (current: {', '.join(existing)}, or press Enter to keep): "
            
        input_str = input(prompt).strip()
        
        if not input_str:
            return existing if existing else []
        
        return parse_people_input(input_str)
    
    def prompt_location(self, existing=None):
        """
        Prompt user for location.
        
        Args:
            existing: Existing location string (if editing)
            
        Returns:
            Location string
        """
        prompt = "  Enter location (or press Enter to skip): "
        if existing:
            prompt = f"  Enter location (current: {existing}, or press Enter to keep): "
            
        input_str = input(prompt).strip()
        return input_str if input_str else (existing if existing else "")
    
    def prompt_date(self, existing=None):
        """
        Prompt user for approximate date.
        
        Args:
            existing: Existing date string (if editing)
            
        Returns:
            Date string
        """
        prompt = "  Enter approximate date (e.g., 'March 1970', or press Enter to skip): "
        if existing:
            prompt = f"  Enter date (current: {existing}, or press Enter to keep): "
            
        input_str = input(prompt).strip()
        return input_str if input_str else (existing if existing else "")
    
    def prompt_notes(self, existing=None):
        """
        Prompt user for additional notes.
        
        Args:
            existing: Existing notes string (if editing)
            
        Returns:
            Notes string
        """
        prompt = "  Enter additional notes (or press Enter to skip): "
        if existing:
            prompt = f"  Enter notes (current: {existing}, or press Enter to keep): "
            
        input_str = input(prompt).strip()
        return input_str if input_str else (existing if existing else "")
    
    def prompt_categories(self, existing=None):
        """
        Prompt user for categories/tags.
        
        Args:
            existing: Existing list of categories (if editing)
            
        Returns:
            List of category strings
        """
        prompt = "  Enter categories/tags (comma-separated, e.g., 'family,beach,1970s', or press Enter to skip): "
        if existing:
            prompt = f"  Enter categories (current: {', '.join(existing)}, or press Enter to keep): "
            
        input_str = input(prompt).strip()
        
        if not input_str:
            return existing if existing else []
        
        return parse_people_input(input_str)  # Reuse the comma-separated parser
    
    def collect_annotations(self, image_path, is_edit=False):
        """
        Collect all annotation fields from user.
        
        Args:
            image_path: Path to the image file
            is_edit: Whether this is an edit operation
            
        Returns:
            Dictionary of annotations or None if cancelled
        """
        self.display_header(image_path)
        
        # Check if annotations already exist
        existing = None
        if self.storage.has_annotations(image_path):
            existing = self.storage.read_annotations(image_path)
            if existing:
                self.display_existing_annotations(existing)
                if is_edit:
                    print("  ✏️  Editing existing annotations...\n")
                else:
                    print("  ⚠️  Annotations already exist for this image.")
                    if not confirm_action("  Do you want to edit them?"):
                        logger.info("User chose to skip editing annotations")
                        return None
                    is_edit = True
        
        # Collect annotations
        print("\n  📝 Annotation Form:")
        print("  (Press Enter to skip any field)\n")
        
        people = self.prompt_people(existing.get("people") if existing else None)
        location = self.prompt_location(existing.get("location") if existing else None)
        date_approximate = self.prompt_date(existing.get("date_approximate") if existing else None)
        notes = self.prompt_notes(existing.get("notes") if existing else None)
        categories = self.prompt_categories(existing.get("categories") if existing else None)
        
        # Build annotation dictionary
        annotations = {
            "filename": Path(image_path).name,
            "people": people,
            "location": location,
            "date_approximate": date_approximate,
            "notes": notes,
            "categories": categories
        }
        
        # Keep the original annotated_at timestamp if editing
        if existing and "annotated_at" in existing:
            annotations["annotated_at"] = existing["annotated_at"]
        
        return annotations
    
    def annotate_image(self, image_path):
        """
        Full annotation workflow for a single image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if annotation was saved, False otherwise
        """
        try:
            annotations = self.collect_annotations(image_path, is_edit=False)
            
            if annotations is None:
                logger.info("Annotation cancelled by user")
                return False
            
            # Save annotations
            success = self.storage.create_annotations(image_path, annotations)
            
            if success:
                print(f"\n  ✅ Annotations saved for {Path(image_path).name}")
                print("  " + "─" * 40)
            else:
                print(f"\n  ❌ Failed to save annotations for {Path(image_path).name}")
                print("  " + "─" * 40)
            
            return success
            
        except KeyboardInterrupt:
            print("\n  ⚠️  Annotation interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Error during annotation of {image_path}: {e}")
            print(f"\n  ❌ Error: {e}")
            return False
    
    def edit_annotations(self, image_path):
        """
        Edit existing annotations for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if annotations were updated, False otherwise
        """
        try:
            if not self.storage.has_annotations(image_path):
                print(f"\n  ⚠️  No existing annotations found for {Path(image_path).name}")
                return False
            
            annotations = self.collect_annotations(image_path, is_edit=True)
            
            if annotations is None:
                logger.info("Edit cancelled by user")
                return False
            
            # Update annotations
            success = self.storage.update_annotations(image_path, annotations)
            
            if success:
                print(f"\n  ✅ Annotations updated for {Path(image_path).name}")
            else:
                print(f"\n  ❌ Failed to update annotations for {Path(image_path).name}")
            
            return success
            
        except KeyboardInterrupt:
            print("\n  ⚠️  Edit interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Error during editing of {image_path}: {e}")
            print(f"\n  ❌ Error: {e}")
            return False
            