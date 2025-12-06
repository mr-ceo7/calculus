"""
Pytest configuration and shared fixtures
Provides reusable test utilities and sample data
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import pytest
from flask import Flask
from flask.testing import FlaskClient

# Add src directory to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from config import TestingConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_pdf_path(temp_dir: Path) -> Path:
    """Create a sample PDF file for testing"""
    # Note: This creates a text file, not a real PDF
    # For real PDF tests, use the data/ directory files
    pdf_path = temp_dir / "test.pdf"
    pdf_path.write_text("Sample PDF content for testing")
    return pdf_path


@pytest.fixture
def sample_txt_path(temp_dir: Path) -> Path:
    """Create a sample text file with course content"""
    txt_path = temp_dir / "test.txt"
    content = """
Chapter 1: Introduction

Definition: A function is a relation between sets.

Theorem: Every continuous function is integrable.

Example: Consider f(x) = x^2.

Chapter 2: Calculus Basics

Definition: The derivative measures rate of change.

Example: The derivative of x^2 is 2x.
"""
    txt_path.write_text(content)
    return txt_path


@pytest.fixture
def sample_malformed_content() -> str:
    """Text content without chapters or special formatting"""
    return "Just some plain text without any structure."


@pytest.fixture
def sample_content_with_definitions() -> str:
    """Text content with definitions for testing detection"""
    return """
Some intro text.

Definition: A set is a collection of objects.

More text here.

Define: The function f maps inputs to outputs.

Conclusion.
"""


@pytest.fixture
def sample_content_with_theorems() -> str:
    """Text content with theorems for testing detection"""
    return """
Introduction.

Theorem: All prime numbers are odd, except 2.

Proposition: The sum of angles in a triangle is 180°.

Lemma: Helper result.

Law of Conservation: Energy cannot be created or destroyed.
"""


@pytest.fixture
def sample_content_with_examples() -> str:
    """Text content with examples for testing detection"""
    return """
Theory section.

Example: Let x = 5, then x + 3 = 8.

Exercise: Solve for x in 2x = 10.

More theory.
"""


@pytest.fixture
def app() -> Flask:
    """Create Flask app with testing configuration"""
    # Import here to avoid circular imports
    from app import create_app
    
    flask_app = create_app('testing')
    flask_app.config['TESTING'] = True
    
    # Ensure test directories exist
    Path(flask_app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(flask_app.config['OUTPUT_FOLDER']).mkdir(parents=True, exist_ok=True)
    
    yield flask_app
    
    # Cleanup test directories
    shutil.rmtree(flask_app.config['UPLOAD_FOLDER'], ignore_errors=True)
    shutil.rmtree(flask_app.config['OUTPUT_FOLDER'], ignore_errors=True)


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create Flask test client"""
    return app.test_client()


@pytest.fixture
def real_pdf_path() -> Path:
    """Path to a real PDF file in the data directory"""
    pdf_path = Path(__file__).parent.parent / 'data' / '0programming paradigms.pdf'
    if pdf_path.exists():
        return pdf_path
    pytest.skip("Real PDF file not found in data directory")


@pytest.fixture
def real_txt_path() -> Path:
    """Path to a real text file in the data directory"""
    txt_path = Path(__file__).parent.parent / 'data' / 'sma103_text.txt'
    if txt_path.exists():
        return txt_path
    pytest.skip("Real text file not found in data directory")
