"""
Unit tests for converter/utils.py
Tests all utility functions for file handling and validation
"""
import pytest
from pathlib import Path
import sys

# Add src directory to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(src_path / 'converter'))

from utils import (
    validate_file_exists,
    validate_file_extension,
    sanitize_filename,
    get_file_size_mb,
    ensure_directory,
    get_safe_output_path
)
from exceptions import InvalidFileError


@pytest.mark.unit
class TestFileValidation:
    """Tests for file validation functions"""
    
    def test_validate_existing_file(self, sample_txt_path):
        """Test validation of existing file passes"""
        validate_file_exists(sample_txt_path)  # Should not raise
        
    def test_validate_nonexistent_file(self, temp_dir):
        """Test validation of nonexistent file raises error"""
        fake_path = temp_dir / "nonexistent.txt"
        with pytest.raises(InvalidFileError, match="does not exist"):
            validate_file_exists(fake_path)
            
    def test_validate_directory_as_file(self, temp_dir):
        """Test that directory is not accepted as file"""
        with pytest.raises(InvalidFileError, match="not a file"):
            validate_file_exists(temp_dir)
            
    def test_validate_allowed_extensions(self, sample_txt_path):
        """Test extension validation with allowed extensions"""
        validate_file_extension(sample_txt_path, {'txt', 'pdf'})  # Should not raise
        
    def test_validate_disallowed_extension(self, temp_dir):
        """Test extension validation rejects disallowed extensions"""
        file_path = temp_dir / "test.jpg"
        file_path.write_text("content")
        
        with pytest.raises(InvalidFileError, match="Invalid extension"):
            validate_file_extension(file_path, {'txt', 'pdf'})


@pytest.mark.unit
class TestFilenameSanitization:
    """Tests for filename sanitization"""
    
    def test_sanitize_unsafe_characters(self):
        """Test removal of unsafe filesystem characters"""
        filename = 'test<>:"/\\|?*file.txt'
        result = sanitize_filename(filename)
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        
    def test_sanitize_preserves_extension(self):
        """Test that file extension is preserved"""
        filename = "test_file.pdf"
        result = sanitize_filename(filename)
        assert result.endswith('.pdf')
        
    def test_sanitize_length_limit(self):
        """Test that filename is truncated to max length"""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name, max_length=100)
        assert len(result) <= 100
        assert result.endswith('.txt')
        
    def test_sanitize_collapses_underscores(self):
        """Test that multiple underscores are collapsed"""
        filename = "test___multiple___underscores.txt"
        result = sanitize_filename(filename)
        assert '___' not in result
        
    def test_sanitize_path_components(self):
        """Test that path components are removed"""
        filename = "../../../etc/passwd"
        result = sanitize_filename(filename)
        assert '/' not in result
        assert '..' not in result


@pytest.mark.unit
class TestFileSize:
    """Tests for file size calculation"""
    
    def test_get_file_size_mb(self, temp_dir):
        """Test file size calculation in MB"""
        test_file = temp_dir / "test.txt"
        # Create 1MB file (approximately)
        test_file.write_text("a" * (1024 * 1024))
        
        size_mb = get_file_size_mb(test_file)
        assert 0.9 < size_mb < 1.1  # Allow some tolerance


@pytest.mark.unit
class TestDirectoryCreation:
    """Tests for directory creation"""
    
    def test_ensure_directory_creates_new(self, temp_dir):
        """Test that ensure_directory creates new directory"""
        new_dir = temp_dir / "new" / "nested" / "dir"
        ensure_directory(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()
        
    def test_ensure_directory_idempotent(self, temp_dir):
        """Test that ensure_directory is idempotent"""
        new_dir = temp_dir / "test_dir"
        ensure_directory(new_dir)
        ensure_directory(new_dir)  # Should not raise
        assert new_dir.exists()


@pytest.mark.unit
class TestSafeOutputPath:
    """Tests for safe output path generation"""
    
    def test_get_safe_output_path(self, temp_dir):
        """Test generation of safe output path"""
        input_path = temp_dir / "My Lecture Notes.pdf"
        output_dir = temp_dir / "outputs"
        
        result = get_safe_output_path(input_path, output_dir)
        
        assert result.parent == output_dir
        assert result.suffix == '.html'
        assert 'smart_notes' in result.name.lower()
        
    def test_safe_output_path_custom_suffix(self, temp_dir):
        """Test custom suffix in output path"""
        input_path = temp_dir / "test.pdf"
        output_dir = temp_dir
        
        result = get_safe_output_path(input_path, output_dir, suffix="_converted")
        
        assert '_converted' in result.name
        assert result.suffix == '.html'
        
    def test_safe_output_path_sanitizes_name(self, temp_dir):
        """Test that unsafe characters are sanitized in output name"""
        input_path = temp_dir / "test<unsafe>name.pdf"
        output_dir = temp_dir
        
        result = get_safe_output_path(input_path, output_dir)
        
        assert '<' not in str(result)
        assert '>' not in str(result)
