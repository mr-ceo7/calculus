# Converter Module

This is the "brain" of the Smart Notes Generator. It converts PDFs and text files into beautiful, interactive HTML study materials.

## Files

### 📄 pdf_to_html.py
**What it does:** Reads PDF files, extracts text, and converts it into formatted HTML.

**Main functions:**
- `parse_pdf()` - Extracts text from PDF files
- `smart_format()` - Detects definitions, theorems, and examples
- `generate_smart_notes()` - Creates the final HTML file

### ⚠️ exceptions.py
**What it does:** Defines custom error types for better error messages.

**Examples:**
- `PDFParsingError` - When a PDF can't be read
- `EmptyContentError` - When a file has no text
- `TemplateNotFoundError` - When the HTML template is missing

### 🔧 utils.py
**What it does:** Helper functions for file operations.

**Examples:**
- `validate_file_exists()` - Check if a file exists
- `sanitize_filename()` - Make filenames safe
- `detect_encoding()` - Figure out file text encoding

### 🎨 smart_template.html
**What it does:** The HTML template that makes the output look beautiful.

Features:
- Dark glassmorphism design
- Tabbed navigation for chapters
- Colored boxes for definitions/theorems
- Mobile-responsive layout

## How Conversion Works

1. **Input** - PDF or TXT file
2. **Parsing** - Extract all text
3. **Detection** - Find definitions, theorems, chapters
4. **Formatting** - Wrap content in styled HTML boxes
5. **Template** - Inject into beautiful template
6. **Output** - Interactive HTML file! 🎉

## For Beginners

Think of this like a smart photocopier:
- Instead of copying pictures of pages...
- It reads the text and understands the structure
- Then creates a beautiful, interactive version!
