"""
Utility functions for file handling and validation
Provides reusable helpers for the converter module
"""
import os
import re
from pathlib import Path
from typing import Optional, Set
import chardet

try:
    from .exceptions import InvalidFileError
except ImportError:
    from exceptions import InvalidFileError


def validate_file_exists(filepath: Path) -> None:
    """
    Validate that a file exists and is readable
    
    Args:
        filepath: Path to the file
        
    Raises:
        InvalidFileError: If file doesn't exist or isn't readable
    """
    if not filepath.exists():
        raise InvalidFileError(str(filepath), "File does not exist")
    
    if not filepath.is_file():
        raise InvalidFileError(str(filepath), "Path is not a file")
    
    if not os.access(filepath, os.R_OK):
        raise InvalidFileError(str(filepath), "File is not readable")


def validate_file_extension(filepath: Path, allowed_extensions: Set[str]) -> None:
    """
    Validate that file has an allowed extension
    
    Args:
        filepath: Path to the file
        allowed_extensions: Set of allowed extensions (without dot)
        
    Raises:
        InvalidFileError: If extension is not allowed
    """
    extension = filepath.suffix.lstrip('.').lower()
    if extension not in allowed_extensions:
        allowed = ', '.join(f'.{ext}' for ext in sorted(allowed_extensions))
        raise InvalidFileError(
            str(filepath),
            f"Invalid extension '.{extension}'. Allowed: {allowed}"
        )


def detect_encoding(filepath: Path) -> str:
    """
    Detect the character encoding of a text file
    
    Args:
        filepath: Path to the text file
        
    Returns:
        Detected encoding (e.g., 'utf-8', 'latin-1')
    """
    with open(filepath, 'rb') as f:
        raw_data = f.read(10000)  # Read first 10KB for detection
    
    result = chardet.detect(raw_data)
    return result['encoding'] or 'utf-8'


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing or replacing unsafe characters
    
    Args:
        filename: Original filename
        max_length: Maximum allowed length
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace unsafe characters with underscore
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Collapse multiple underscores
    filename = re.sub(r'_{2,}', '_', filename)
    
    # Trim to max length while preserving extension
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext
    
    return filename.strip('._')


def get_file_size_mb(filepath: Path) -> float:
    """
    Get file size in megabytes
    
    Args:
        filepath: Path to the file
        
    Returns:
        File size in MB
    """
    size_bytes = filepath.stat().st_size
    return size_bytes / (1024 * 1024)


def ensure_directory(directory: Path) -> None:
    """
    Ensure a directory exists, create if necessary
    
    Args:
        directory: Path to the directory
    """
    directory.mkdir(parents=True, exist_ok=True)


def get_safe_output_path(input_path: Path, output_dir: Path, suffix: str = "_smart_notes") -> Path:
    """
    Generate a safe output path based on input filename
    
    Args:
        input_path: Input file path
        output_dir: Directory for output file
        suffix: Suffix to add before extension
        
    Returns:
        Safe output file path
    """
    # Get base name without extension
    base_name = input_path.stem
    
    # Sanitize the base name
    safe_name = sanitize_filename(base_name)
    
    # Create output filename
    output_filename = f"{safe_name}{suffix}.html"
    
    return output_dir / output_filename
