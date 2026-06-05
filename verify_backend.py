import os
import json
import unittest
import tempfile
from pathlib import Path
from app import app, config, save_config, stop_watcher

class BackendTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Create a temporary directory for scanning tests
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_dir_path = Path(self.test_dir.name)
        
        # Write some dummy image files
        self.jpg_file = self.test_dir_path / "slide_01.jpg"
        self.jpg_file.write_text("dummy_jpg_data")
        
        self.cr3_file = self.test_dir_path / "slide_02.cr3"
        self.cr3_file.write_text("dummy_cr3_data")
        
        # Save original config to restore later
        self.original_dir = config['target_directory']
        self.original_mode = config['mode']
        
        # Set config to use our temp test directory
        config['target_directory'] = str(self.test_dir_path)
        config['mode'] = 'scan'

    def tearDown(self):
        # Clean up temp folder, stop watcher, and restore config
        stop_watcher()
        self.test_dir.cleanup()
        config['target_directory'] = self.original_dir
        config['mode'] = self.original_mode
        save_config()

    def test_get_config(self):
        """Test getting current config."""
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['target_directory'], str(self.test_dir_path))
        self.assertEqual(data['mode'], 'scan')
        self.assertIn('has_rawpy', data)

    def test_post_config_success(self):
        """Test setting config with valid directory."""
        response = self.client.post('/api/config', json={
            'target_directory': str(self.test_dir_path),
            'mode': 'hotfolder'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(config['mode'], 'hotfolder')

    def test_post_config_invalid_dir(self):
        """Test setting config with invalid directory."""
        response = self.client.post('/api/config', json={
            'target_directory': '/nonexistent/directory/path/here',
            'mode': 'scan'
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_get_images(self):
        """Test scanning directory for images."""
        response = self.client.get('/api/images')
        self.assertEqual(response.status_code, 200)
        images = json.loads(response.data)
        
        # Should detect two files: slide_01.jpg and slide_02.cr3
        self.assertEqual(len(images), 2)
        names = [img['name'] for img in images]
        self.assertIn('slide_01.jpg', names)
        self.assertIn('slide_02.cr3', names)
        
        # Check type parsing
        jpg_item = next(img for img in images if img['name'] == 'slide_01.jpg')
        self.assertEqual(jpg_item['type'], 'jpg')
        self.assertFalse(jpg_item['annotated'])

    def test_annotation_flow(self):
        """Test getting, writing and retrieving annotations sidecars."""
        # 1. Get empty/skeleton annotations for slide_01.jpg
        response = self.client.get('/api/annotation?path=slide_01.jpg')
        self.assertEqual(response.status_code, 200)
        meta = json.loads(response.data)
        self.assertEqual(meta['subject'], '')
        self.assertEqual(meta['tags'], [])

        # 2. Write annotations
        payload = {
            'subject': 'Family Picnic',
            'date': 'July 1980',
            'location': 'Yosemite',
            'description': 'Mom and Dad near the lake',
            'tags': ['family', 'lake', '1980'],
            'custom': {'Box Number': 'Slide Box 4'}
        }
        response = self.client.post('/api/annotation?path=slide_01.jpg', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.data)['success'])

        # Check sidecar JSON file exists in directory
        sidecar_file = self.test_dir_path / "slide_01.json"
        self.assertTrue(sidecar_file.exists())

        # 3. Read back annotation and verify
        response = self.client.get('/api/annotation?path=slide_01.jpg')
        self.assertEqual(response.status_code, 200)
        saved_meta = json.loads(response.data)
        self.assertEqual(saved_meta['subject'], 'Family Picnic')
        self.assertEqual(saved_meta['location'], 'Yosemite')
        self.assertEqual(saved_meta['tags'], ['family', 'lake', '1980'])
        self.assertEqual(saved_meta['custom']['Box Number'], 'Slide Box 4')
        self.assertIn('annotated_at', saved_meta)

        # 4. Read list of images again and verify marked as annotated
        response = self.client.get('/api/images')
        images = json.loads(response.data)
        jpg_item = next(img for img in images if img['name'] == 'slide_01.jpg')
        self.assertTrue(jpg_item['annotated'])

if __name__ == '__main__':
    unittest.main()
