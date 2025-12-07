"""
Integration tests for Flask application routes
Tests file uploads, error handling, and HTTP responses
"""
import pytest
import io
from pathlib import Path


@pytest.mark.integration
class TestHomePage:
    """Tests for the home page"""
    
    def test_homepage_loads(self, client):
        """Test that homepage loads successfully"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Smart Notes Generator' in response.data
        
    def test_homepage_has_upload_form(self, client):
        """Test that homepage contains upload form"""
        response = client.get('/')
        assert b'<form' in response.data
        assert b'file' in response.data


@pytest.mark.integration
class TestFileUpload:
    """Tests for file upload functionality"""
    
    def test_upload_txt_file(self, client, sample_txt_path):
        """Test successful upload and conversion of text file"""
        with open(sample_txt_path, 'rb') as f:
            data = {
                'file': (f, 'test.txt')
            }
            response = client.post('/upload', data=data, follow_redirects=False)
        
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['success'] is True
        assert 'preview_url' in payload
        preview = client.get(payload['preview_url'])
        assert preview.status_code == 200
        assert b'<!DOCTYPE html>' in preview.data
        
    def test_upload_no_file(self, client):
        """Test upload with no file selected"""
        response = client.post('/upload', data={}, follow_redirects=True)
        assert response.status_code == 400
        payload = response.get_json()
        assert payload['success'] is False
        
    def test_upload_empty_filename(self, client):
        """Test upload with empty filename"""
        data = {
            'file': (io.BytesIO(b''), '')
        }
        response = client.post('/upload', data=data, follow_redirects=True)
        assert response.status_code == 400
        
    def test_upload_invalid_extension(self, client, temp_dir):
        """Test upload with invalid file extension"""
        invalid_file = temp_dir / "test.jpg"
        invalid_file.write_bytes(b"fake image content")
        
        with open(invalid_file, 'rb') as f:
            data = {
                'file': (f, 'test.jpg')
            }
            response = client.post('/upload', data=data, follow_redirects=True)
        
        assert response.status_code == 400


@pytest.mark.integration
class TestErrorHandling:
    """Tests for error handling and edge cases"""
    
    def test_upload_malformed_content(self, client, temp_dir):
        """Test handling of malformed/empty content"""
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")
        
        with open(empty_file, 'rb') as f:
            data = {
                'file': (f, 'empty.txt')
            }
            response = client.post('/upload', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['success'] is True
        preview = client.get(payload['preview_url'])
        assert preview.status_code == 200
        
    def test_favicon_route(self, client):
        """Test that favicon route exists"""
        response = client.get('/favicon.ico')
        # Should either return favicon or 404, not 500
        assert response.status_code in [200, 404]


@pytest.mark.integration
@pytest.mark.slow
class TestRealFileConversion:
    """Integration tests with real files from data directory"""
    
    def test_convert_real_txt_file(self, client, real_txt_path):
        """Test conversion of real text file"""
        with open(real_txt_path, 'rb') as f:
            data = {
                'file': (f, real_txt_path.name)
            }
            response = client.post('/upload', data=data, follow_redirects=False)
        
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['success'] is True
        preview = client.get(payload['preview_url'])
        assert preview.status_code == 200
        assert b'<html' in preview.data.lower()
        
    def test_convert_real_pdf_file(self, client, real_pdf_path):
        """Test conversion of real PDF file"""
        with open(real_pdf_path, 'rb') as f:
            data = {
                'file': (f, real_pdf_path.name)
            }
            response = client.post('/upload', data=data, follow_redirects=False)
        
        assert response.status_code in [200, 400, 500]


@pytest.mark.integration
class TestFileCleanup:
    """Tests for temporary file cleanup"""
    
    def test_uploaded_file_cleaned_up(self, client, app, sample_txt_path):
        """Test that uploaded files are cleaned up after processing"""
        upload_folder = Path(app.config['UPLOAD_FOLDER'])
        initial_files = set(upload_folder.iterdir()) if upload_folder.exists() else set()
        
        with open(sample_txt_path, 'rb') as f:
            data = {
                'file': (f, 'test_cleanup.txt')
            }
            client.post('/upload', data=data, follow_redirects=False)
        
        # Check that upload folder doesn't have additional files
        final_files = set(upload_folder.iterdir()) if upload_folder.exists() else set()
        new_files = final_files - initial_files
        
        # The uploaded file should have been cleaned up
        assert len([f for f in new_files if f.name == 'test_cleanup.txt']) == 0
