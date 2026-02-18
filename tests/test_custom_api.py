
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from converter import custom_ai_api

# Test _get_active_endpoint
def test_get_active_endpoint_success():
    with patch('requests.get') as mock_get:
        # First endpoint fails, second succeeds
        mock_get.side_effect = [
            requests.RequestException("Connection refused"),
            MagicMock(status_code=200)
        ]
        
        endpoint = custom_ai_api._get_active_endpoint()
        assert endpoint == custom_ai_api.POSSIBLE_ENDPOINTS[1]
        assert mock_get.call_count == 2

def test_get_active_endpoint_all_fail():
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.RequestException("Connection refused")
        
        with pytest.raises(custom_ai_api.CustomAPIUnavailable):
            custom_ai_api._get_active_endpoint()

# Test upload_file
def test_upload_file_success():
    with patch('converter.custom_ai_api._get_active_endpoint', return_value="http://test-server"):
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"filename": "test.pdf", "extracted_txt": "test.txt"}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # Create a dummy file for testing
            dummy_path = Path("test_dummy.pdf")
            dummy_path.touch()
            try:
                result = custom_ai_api.upload_file(dummy_path)
                assert result['filename'] == "test.pdf"
                mock_post.assert_called_once()
            finally:
                dummy_path.unlink()

def test_upload_file_failure():
    with patch('converter.custom_ai_api._get_active_endpoint', return_value="http://test-server"):
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.RequestException("Upload failed")
            
            dummy_path = Path("test_dummy_fail.pdf")
            dummy_path.touch()
            try:
                with pytest.raises(custom_ai_api.CustomAPIUnavailable):
                    custom_ai_api.upload_file(dummy_path)
            finally:
                dummy_path.unlink()

# Test generate_completion
def test_generate_completion_success():
    with patch('converter.custom_ai_api._get_active_endpoint', return_value="http://test-server"):
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "<html>Content</html>"}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            result = custom_ai_api.generate_completion("Test prompt", "test.txt")
            assert result == "<html>Content</html>"

import requests
