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

    def test_raw_to_jpeg_sidecar_sharing(self):
        """Test that a CR3 and JPG sharing the same base name share the same sidecar annotations."""
        # 1. Write annotation for slide_02.cr3
        payload = {
            'subject': 'Shared Sunset',
            'date': '2026-06-05',
            'location': 'Beach',
            'description': 'Taken on RAW',
            'tags': ['raw'],
            'custom': {}
        }
        response = self.client.post('/api/annotation?path=slide_02.cr3', json=payload)
        self.assertEqual(response.status_code, 200)

        # 2. Check that the sidecar file was created as slide_02.json (not slide_02.cr3.json)
        sidecar_file = self.test_dir_path / "slide_02.json"
        self.assertTrue(sidecar_file.exists())

        # 3. Simulate editing to JPEG (creating slide_02.jpg in same dir)
        jpeg_file = self.test_dir_path / "slide_02.jpg"
        jpeg_file.write_text("dummy_jpg_data")

        # 4. Fetch annotation for the new JPEG file (slide_02.jpg)
        response = self.client.get('/api/annotation?path=slide_02.jpg')
        self.assertEqual(response.status_code, 200)
        jpeg_meta = json.loads(response.data)
        
        # Verify it picks up the same annotations written for the CR3 file
        self.assertEqual(jpeg_meta['subject'], 'Shared Sunset')
        self.assertEqual(jpeg_meta['location'], 'Beach')
        self.assertEqual(jpeg_meta['tags'], ['raw'])

    def test_ml_disabled_graceful_fallback(self):
        """Test that the app reports ML status and falls back gracefully when ML is disabled or handles analyzer commands."""
        # 1. Fetch config and check has_ml presence
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('has_ml', data)
        
        has_ml = data['has_ml']

        # 2. Query /api/analyze and verify it returns a 400 error indicating ML is disabled ONLY if has_ml is False
        response = self.client.post('/api/analyze?path=slide_01.jpg')
        if not has_ml:
            self.assertEqual(response.status_code, 400)
            res_data = json.loads(response.data)
            self.assertIn('error', res_data)
            self.assertIn('ML analyzer is not enabled', res_data['error'])
        else:
            # If ML is enabled, querying /api/analyze on a dummy file slide_01.jpg (which contains text 'dummy_jpg_data')
            # should try to process the image and fail because it's not a real image, yielding a 500 error or similar,
            # but NOT a 400 'ML analyzer is not enabled' error.
            self.assertNotEqual(response.status_code, 400)

    def test_annotation_includes_ai_features(self):
        """Test that ai_features are correctly serialized and deserialized in sidecars."""
        payload = {
            'subject': 'Mountain Climbing',
            'date': '1995',
            'location': 'Alps',
            'description': 'AI features test',
            'tags': ['alps'],
            'custom': {},
            'ai_features': [
                {'feature': 'mountain', 'confidence': 94.2},
                {'feature': 'snow', 'confidence': 88.5}
            ]
        }
        
        # Write
        response = self.client.post('/api/annotation?path=slide_01.jpg', json=payload)
        self.assertEqual(response.status_code, 200)
        
        # Read
        response = self.client.get('/api/annotation?path=slide_01.jpg')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify
        self.assertIn('ai_features', data)
        self.assertEqual(len(data['ai_features']), 2)
        self.assertEqual(data['ai_features'][0]['feature'], 'mountain')
        self.assertEqual(data['ai_features'][0]['confidence'], 94.2)

    def test_people_autocomplete_and_serialization(self):
        """Test that people field is serialized correctly in sidecar, and api_people aggregates unique sorted names."""
        # 1. Write annotations with people for slide_01.jpg
        payload_1 = {
            'subject': 'Family Reunion',
            'date': '1990',
            'location': 'Grandmas House',
            'description': 'Family group photo',
            'tags': ['reunion'],
            'people': ['Alice Smith', 'Bob Jones'],
            'custom': {}
        }
        response = self.client.post('/api/annotation?path=slide_01.jpg', json=payload_1)
        self.assertEqual(response.status_code, 200)

        # 2. Write annotations with people for slide_02.cr3 (sharing base name slide_02.json)
        payload_2 = {
            'subject': 'Hiking trip',
            'date': '1995',
            'location': 'Yosemite',
            'description': 'Alice and Charlie hiking',
            'tags': ['hiking'],
            'people': ['Charlie Brown', 'Alice Smith'],
            'custom': {}
        }
        response = self.client.post('/api/annotation?path=slide_02.cr3', json=payload_2)
        self.assertEqual(response.status_code, 200)

        # 3. Read back annotations for slide_01.jpg and verify people are in it
        response = self.client.get('/api/annotation?path=slide_01.jpg')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['people'], ['Alice Smith', 'Bob Jones'])

        # 4. Check api_people compiles unique sorted names
        response = self.client.get('/api/people')
        self.assertEqual(response.status_code, 200)
        people = json.loads(response.data)
        
        # Expected list should be unique, sorted alphabetically: ['Alice Smith', 'Bob Jones', 'Charlie Brown']
        self.assertEqual(people, ['Alice Smith', 'Bob Jones', 'Charlie Brown'])

if __name__ == '__main__':
    unittest.main()
