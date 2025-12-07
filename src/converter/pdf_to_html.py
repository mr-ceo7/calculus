import sys
import re
import os
import logging
import html
from pathlib import Path
from typing import Optional, List, Dict
from pypdf import PdfReader

# Support both standalone and package usage
try:
    from .exceptions import PDFParsingError, TemplateNotFoundError, EmptyContentError
    from .utils import validate_file_exists, validate_file_extension, get_safe_output_path
except ImportError:
    from exceptions import PDFParsingError, TemplateNotFoundError, EmptyContentError
    from utils import validate_file_exists, validate_file_extension, get_safe_output_path

# Configure logging
logger = logging.getLogger(__name__)

def parse_pdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text content
        
    Raises:
        PDFParsingError: If PDF cannot be parsed
        EmptyContentError: If no text could be extracted
    """
    try:
        logger.info(f"Parsing PDF: {pdf_path}")
        reader = PdfReader(str(pdf_path))
        text = ""
        
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                text += page.extract_text() + "\n"
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                raise PDFParsingError(str(pdf_path), page=page_num, original_error=e)
        
        if not text.strip():
            raise EmptyContentError(str(pdf_path))
        
        logger.info(f"Successfully extracted {len(text)} characters from PDF")
        return text
        
    except EmptyContentError:
        raise
    except PDFParsingError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing PDF: {e}")
        raise PDFParsingError(str(pdf_path), original_error=e)

def smart_format(text: str) -> str:
    """
    Applies regex heuristics to wrap content in Glassmorphism boxes.
    
    Args:
        text: Raw text content to format
        
    Returns:
        HTML-formatted content with styled boxes
    """
    lines = text.split('\n')
    html_output = ""
    
    # Regex Patterns
    # Header: Short, uppercase or ends in colon, not a sentence
    header_pattern = re.compile(r'^([A-Z][A-Z\s\d\-\.]+|.{1,50}:)$') 
    
    # Box Triggers
    def_pattern = re.compile(r'^\s*(Definition|Define)\b[:\.]?(.*)', re.IGNORECASE)
    thm_pattern = re.compile(r'^\s*(Theorem|Proposition|Lemma|Law)\b[:\.]?(.*)', re.IGNORECASE)
    ex_pattern = re.compile(r'^\s*(Example|Exercise)\b[:\.]?(.*)', re.IGNORECASE)
    
    in_box = False
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Check for Box Starts
        def_match = def_pattern.match(line)
        thm_match = thm_pattern.match(line)
        ex_match = ex_pattern.match(line)
        
        if def_match:
            if in_box: html_output += "</div>\n" # Close prev
            title = def_match.group(1) + " " + def_match.group(2)
            html_output += f'<div class="definition-box"><span class="definition-title">{title}</span>\n'
            in_box = True
            continue
            
        if thm_match:
            if in_box: html_output += "</div>\n"
            title = thm_match.group(1) + " " + thm_match.group(2)
            html_output += f'<div class="theorem-box"><span class="theorem-title">{title}</span>\n'
            in_box = True
            continue
            
        if ex_match:
            if in_box: html_output += "</div>\n"
            title = ex_match.group(1) + " " + ex_match.group(2)
            html_output += f'<div class="example-box"><div class="example-badge">Example</div><div class="example-header">{title}</div>\n'
            in_box = True
            continue
            
        # Headers (End box if hit header)
        if header_pattern.match(line) and len(line) > 3:
             if in_box: 
                 html_output += "</div>\n"
                 in_box = False
             html_output += f'<h3>{line}</h3>\n'
             continue
             
        # Normal Text
        # Detect Math (simple heuristic)
        if '$' in line or '\\' in line or '=' in line:
            # Maybe wrap in <p> tag?
            pass

        html_output += f'<p>{line}</p>\n'
        
    if in_box: html_output += "</div>\n"
    return html_output

def generate_smart_notes(
    input_path: str | Path,
    output_path: str | Path,
    template_path: Optional[str | Path] = None,
    text_content: Optional[str] = None
) -> None:
    """
    Generate smart notes HTML from PDF or text content
    
    Args:
        input_path: Path to input file (PDF or TXT)
        output_path: Path where HTML output will be saved
        template_path: Path to HTML template (optional, uses default if None)
        text_content: Pre-extracted text content (optional, extracts from file if None)
        
    Raises:
        TemplateNotFoundError: If template file doesn't exist
        PDFParsingError: If PDF parsing fails
        EmptyContentError: If no content extracted
    """
    # Convert to Path objects
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    # Determine template path
    if template_path is None:
        # Use template in same directory as this script
        template_path = Path(__file__).parent / "smart_template.html"
    else:
        template_path = Path(template_path)
    
    # Validate template exists
    if not template_path.exists():
        raise TemplateNotFoundError(str(template_path))
    
    # Get content
    if text_content is not None:
        full_text = text_content
        logger.info(f"Using provided text content ({len(text_content)} chars)")
    else:
        logger.info(f"Reading {input_path}...")
        full_text = parse_pdf(input_path)
    
    # Split into Chapters for Tabs
    # Heuristic: Look for "Chapter X" or "Unit X"
    # If not found, split arbitrarily or keep as one.
    
    chapter_pattern = re.compile(r'^\s*(Chapter|Unit|Module)\s+\d+', re.IGNORECASE | re.MULTILINE)
    matches = list(chapter_pattern.finditer(full_text))
    
    tabs: List[Dict[str, str]] = []
    
    if not matches:
        # Fallback: Treat as single chapter
        logger.info("No chapters detected, treating as single document")
        tabs.append({"title": "Full Notes", "content": smart_format(full_text)})
    else:
        logger.info(f"Detected {len(matches)} chapters/units")
        for i in range(len(matches)):
            start = matches[i].start()
            end = matches[i+1].start() if i + 1 < len(matches) else len(full_text)
            
            # Extract Title
            chunk = full_text[start:end]
            lines = chunk.split('\n')
            title = lines[0].strip() if lines else f"Chapter {i+1}"
            
            # Format Content
            content = smart_format(chunk)
            tabs.append({"title": title, "content": content})
            
    # Generate HTML
    nav_html = ""
    content_html = ""
    
    for i, tab in enumerate(tabs):
        tab_id = i + 1
        active_class = " active" if i == 0 else ""
        
        # Content
        content_html += f'<div id="tab-{tab_id}" class="tab-section{active_class}">\n'
        content_html += f'<section class="glass-panel"><h2>{tab["title"]}</h2>\n'
        content_html += tab['content']
        content_html += '</section></div>\n'
        
        # Nav (fallback to Part N when title missing/long; escape quotes for inline JS)
        raw_title = (tab['title'] or '').strip() or f"Part {tab_id}"
        safe_title_js = raw_title.replace("'", "\\'")
        safe_title_attr = html.escape(raw_title, quote=True)
        short_title = (raw_title.split(':')[0] or raw_title).strip()
        if len(short_title) > 12:
            short_title = f"Part {tab_id}"

        nav_html += f'''
        <div class="nav-item{active_class}" data-title="{safe_title_attr}" aria-label="{safe_title_attr}" role="button" tabindex="0" onclick="switchTab({tab_id}, '{safe_title_js}')">
            <span class="nav-icon">●</span>
            <span>{short_title}</span>
        </div>
        '''
        
    # Read Template
    logger.info(f"Loading template from {template_path}")
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    if '<!-- AI GENERATED CONTENT GOES HERE -->' not in template:
        logger.warning("Template missing content placeholder; output may be empty")
    if '<!-- NAV ITEMS GENERATED HERE -->' not in template:
        logger.warning("Template missing nav placeholder; navigation may be empty")

    if not content_html.strip():
        logger.warning("Generated content is empty before template substitution")
    if not nav_html.strip():
        logger.warning("Generated navigation is empty before template substitution")
        
    final_html = template.replace('<!-- AI GENERATED CONTENT GOES HERE -->', content_html).replace('<!-- NAV ITEMS GENERATED HERE -->', nav_html)

    if '<!-- AI GENERATED CONTENT GOES HERE -->' in final_html or '<!-- NAV ITEMS GENERATED HERE -->' in final_html:
        logger.warning("Placeholders still present after substitution; check template markers")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    logger.info(f"Success! Generated {output_path}")
    print(f"Success! Generated {output_path}")

if __name__ == "__main__":
    # Configure logging for CLI usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_html.py <input_file>")
        print("Supported formats: .pdf, .txt")
        sys.exit(1)
    
    try:
        input_file = Path(sys.argv[1])
        output_file = Path("Generated_Smart_Notes.html")
        
        # Validate input file
        validate_file_exists(input_file)
        validate_file_extension(input_file, {'pdf', 'txt'})
        
        if input_file.suffix.lower() == '.pdf':
            generate_smart_notes(input_file, output_file)
        elif input_file.suffix.lower() == '.txt':
            # Text file support for testing
            logger.info(f"Reading text file {input_file}...")
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            generate_smart_notes(input_file, output_file, text_content=text)
        else:
            print("Unsupported file type. Use .pdf or .txt")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        sys.exit(1)
