"""
Custom exceptions for the Smart Notes converter
Provides detailed error context for debugging and user-friendly messages
"""
from typing import Optional


class ConversionError(Exception):
    """Base exception for all conversion-related errors"""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.detail:
            return f"{self.message}\nDetail: {self.detail}"
        return self.message


class InvalidFileError(ConversionError):
    """Raised when input file is invalid or cannot be read"""
    
    def __init__(self, filename: str, reason: str):
        message = f"Invalid file: {filename}"
        super().__init__(message, detail=reason)
        self.filename = filename
        self.reason = reason


class PDFParsingError(ConversionError):
    """Raised when PDF cannot be parsed or is corrupted"""
    
    def __init__(self, filename: str, page: Optional[int] = None, original_error: Optional[Exception] = None):
        if page is not None:
            message = f"Failed to parse PDF '{filename}' at page {page}"
        else:
            message = f"Failed to parse PDF '{filename}'"
        
        detail = str(original_error) if original_error else None
        super().__init__(message, detail=detail)
        self.filename = filename
        self.page = page
        self.original_error = original_error


class TemplateNotFoundError(ConversionError):
    """Raised when HTML template file cannot be found"""
    
    def __init__(self, template_path: str):
        message = f"Template file not found: {template_path}"
        detail = "Ensure smart_template.html exists in the converter directory"
        super().__init__(message, detail=detail)
        self.template_path = template_path


class EmptyContentError(ConversionError):
    """Raised when extracted content is empty"""
    
    def __init__(self, filename: str):
        message = f"No content could be extracted from '{filename}'"
        detail = "The file may be empty, corrupted, or contain only images"
        super().__init__(message, detail=detail)
        self.filename = filename
