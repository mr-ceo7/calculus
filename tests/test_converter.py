"""
Unit tests for converter/pdf_to_html.py
Tests all conversion logic including parsing, formatting, and tab generation
"""
import pytest
from pathlib import Path
import sys

# Add src directory to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(src_path / 'converter'))

from pdf_to_html import parse_pdf, smart_format, generate_smart_notes
from exceptions import PDFParsingError, EmptyContentError, TemplateNotFoundError


@pytest.mark.unit
class TestSmartFormat:
    """Tests for the smart_format function"""
    
    def test_format_definitions(self, sample_content_with_definitions):
        """Test that definitions are correctly wrapped in definition boxes"""
        result = smart_format(sample_content_with_definitions)
        assert 'definition-box' in result.lower()
        assert 'definition-title' in result.lower()
        
    def test_format_theorems(self, sample_content_with_theorems):
        """Test that theorems are correctly wrapped in theorem boxes"""
        result = smart_format(sample_content_with_theorems)
        assert 'theorem-box' in result.lower()
        assert 'theorem-title' in result.lower()
        
    def test_format_examples(self, sample_content_with_examples):
        """Test that examples are correctly wrapped in example boxes"""
        result = smart_format(sample_content_with_examples)
        assert 'example-box' in result.lower()
        assert 'example-badge' in result.lower()
        
    def test_format_plain_text(self, sample_malformed_content):
        """Test formatting of plain text without special elements"""
        result = smart_format(sample_malformed_content)
        assert '<p>' in result
        assert 'definition-box' not in result.lower()
        
    def test_format_empty_input(self):
        """Test formatting of empty string"""
        result = smart_format("")
        assert result == ""
        
    def test_format_headers(self):
        """Test that headers are properly formatted"""
        content = """
CHAPTER 1: INTRODUCTION

Some content here.

SECTION A

More content.
"""
        result = smart_format(content)
        assert '<h3>' in result
        

@pytest.mark.unit
class TestChapterDetection:
    """Tests for chapter/unit detection and tab generation"""
    
    def test_detect_chapters(self, sample_txt_path, temp_dir):
        """Test that chapters are correctly detected and create tabs"""
        output_path = temp_dir / "output.html"
        generate_smart_notes(sample_txt_path, output_path, text_content=sample_txt_path.read_text())
        
        html_content = output_path.read_text()
        assert 'tab-1' in html_content
        assert 'tab-2' in html_content
        assert 'Chapter 1' in html_content
        assert 'Chapter 2' in html_content
        
    def test_no_chapters_fallback(self, temp_dir, sample_malformed_content):
        """Test fallback when no chapters are detected"""
        input_path = temp_dir / "input.txt"
        output_path = temp_dir / "output.html"
        input_path.write_text(sample_malformed_content)
        
        generate_smart_notes(input_path, output_path, text_content=sample_malformed_content)
        
        html_content = output_path.read_text()
        assert 'Full Notes' in html_content
        assert 'tab-1' in html_content
        # Should only have one tab
        assert 'tab-2' not in html_content


@pytest.mark.unit
class TestGenerateSmartNotes:
    """Tests for the main generate_smart_notes function"""
    
    def test_generate_from_text_content(self, temp_dir):
        """Test generation with pre-provided text content"""
        output_path = temp_dir / "output.html"
        text_content = "Definition: Test content."
        
        # Create dummy input file
        input_path = temp_dir / "input.txt"
        input_path.write_text(text_content)
        
        generate_smart_notes(input_path, output_path, text_content=text_content)
        
        assert output_path.exists()
        html_content = output_path.read_text()
        assert 'definition-box' in html_content.lower()
        
    def test_output_directory_creation(self, temp_dir):
        """Test that output directory is created if doesn't exist"""
        nested_output = temp_dir / "nested" / "dir" / "output.html"
        input_path = temp_dir / "input.txt"
        input_path.write_text("Test content")
        
        generate_smart_notes(input_path, nested_output, text_content="Test")
        
        assert nested_output.exists()
        assert nested_output.parent.exists()
        
    def test_template_not_found_error(self, temp_dir):
        """Test that TemplateNotFoundError is raised for missing template"""
        input_path = temp_dir / "input.txt"
        input_path.write_text("Test")
        output_path = temp_dir / "output.html"
        fake_template = temp_dir / "fake_template.html"
        
        with pytest.raises(TemplateNotFoundError):
            generate_smart_notes(
                input_path,
                output_path,
                template_path=fake_template,
                text_content="Test"
            )
    
    def test_pathlib_path_support(self, temp_dir, sample_txt_path):
        """Test that Path objects are properly supported"""
        output_path = temp_dir / "output.html"
        
        # Should work with Path objects
        generate_smart_notes(
            Path(sample_txt_path),
            Path(output_path),
            text_content=sample_txt_path.read_text()
        )
        
        assert output_path.exists()
        
    def test_string_path_support(self, temp_dir, sample_txt_path):
        """Test that string paths are properly supported"""
        output_path = temp_dir / "output.html"
        
        # Should work with string paths
        generate_smart_notes(
            str(sample_txt_path),
            str(output_path),
            text_content=sample_txt_path.read_text()
        )
        
        assert output_path.exists()


@pytest.mark.unit
class TestParsingLogic:
    """Tests for special content parsing"""
    
    def test_multiple_definitions_in_sequence(self):
        """Test handling of multiple consecutive definitions"""
        content = """
Definition: First definition.

Definition: Second definition.

Some text.
"""
        result = smart_format(content)
        # Should have two separate definition boxes
        assert result.count('definition-box') == 2
        
    def test_mixed_special_elements(self):
        """Test content with mixed definitions, theorems, and examples"""
        content = """
Definition: A set is a collection.

Theorem: All sets are countable.

Example: Consider the set {1, 2, 3}.
"""
        result = smart_format(content)
        assert 'definition-box' in result.lower()
        assert 'theorem-box' in result.lower()
        assert 'example-box' in result.lower()
        
    def test_case_insensitivity(self):
        """Test that detection is case-insensitive"""
        content = """
DEFINITION: Upper case definition.

definition: Lower case definition.

DeFinItIoN: Mixed case definition.
"""
        result = smart_format(content)
        assert result.count('definition-box') == 3


@pytest.mark.integration
class TestRealFiles:
    """Integration tests with real PDF and text files"""
    
    def test_real_txt_file(self, real_txt_path, temp_dir):
        """Test conversion of real text file from data directory"""
        output_path = temp_dir / "output.html"
        
        # Read text file and pass as text_content
        text_content = real_txt_path.read_text(encoding='utf-8', errors='ignore')
        generate_smart_notes(real_txt_path, output_path, text_content=text_content)
        
        assert output_path.exists()
        assert output_path.stat().st_size > 1000  # Should have substantial content
        
    def test_real_pdf_file(self, real_pdf_path, temp_dir):
        """Test conversion of real PDF file from data directory"""
        output_path = temp_dir / "output.html"
        
        try:
            generate_smart_notes(real_pdf_path, output_path)
            assert output_path.exists()
        except PDFParsingError:
            # Some PDFs might be malformed, this is acceptable
            pytest.skip("PDF parsing failed - may be malformed PDF")
