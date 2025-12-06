import sys
import re
import os
from pypdf import PdfReader

def parse_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def smart_format(text):
    """
    Applies regex heuristics to wrap content in Glassmorphism boxes.
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

def generate_smart_notes(input_path, output_path, template_path="smart_template.html", text_content=None):
    if text_content:
        full_text = text_content
    else:
        print(f"Reading {input_path}...")
        full_text = parse_pdf(input_path)
    
    # Split into Chapters for Tabs
    # Heuristic: Look for "Chapter X" or "Unit X"
    # If not found, split arbitrarily or keep as one.
    
    chapter_pattern = re.compile(r'^\s*(Chapter|Unit|Module)\s+\d+', re.IGNORECASE | re.MULTILINE)
    matches = list(chapter_pattern.finditer(full_text))
    
    tabs = []
    
    if not matches:
        # Fallback: Treat as single chapter
        tabs.append({"title": "Full Notes", "content": smart_format(full_text)})
    else:
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
        
        # Nav
        short_title = tab['title'].split(':')[0] # simple short title
        if len(short_title) > 10: short_title = f"Part {tab_id}"
        
        nav_html += f'''
        <div class="nav-item{active_class}" onclick="switchTab({tab_id}, '{tab["title"]}')">
            <span class="nav-icon">●</span>
            <span>{short_title}</span>
        </div>
        '''
        
    # Read Template
    with open(template_path, 'r') as f:
        template = f.read()
        
    final_html = template.replace('{{CONTENT}}', content_html).replace('{{NAV}}', nav_html)
    
    with open(output_path, 'w') as f:
        f.write(final_html)
        
    print(f"Success! Generated {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_html.py <input_file>")
    else:
        input_file = sys.argv[1]
        output_file = "Generated_Smart_Notes.html"
        
        if input_file.lower().endswith('.pdf'):
            generate_smart_notes(input_file, output_file)
        elif input_file.lower().endswith('.txt'):
            # Text file support for testing
            print(f"Reading text file {input_file}...")
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            # Use same logic but skip parse_pdf
            # Copy-paste generate_smart_notes logic or refactor? 
            # Refactoring slightly to reuse generate logic
            generate_smart_notes(input_file, output_file, text_content=text)
        else:
            print("Unsupported file type. Use .pdf or .txt")
