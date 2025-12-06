# Smart Notes Generator

Transform PDF lecture notes into beautiful, interactive HTML learning materials with automatic formatting for definitions, theorems, and examples.

## 🎨 Features

- **Modern Glassmorphism Design**: Stunning dark theme with frosted glass effects
- **Auto-Detection**: Automatically identifies and formats definitions, theorems, and examples
- **Interactive Elements**: Tab-based navigation, collapsible sections, and smooth animations
- **Web Interface**: User-friendly drag-and-drop upload interface
- **Command Line**: Simple Python script for batch processing
- **MathJax Support**: Renders mathematical equations beautifully

## 🚀 Quick Start

### Environment

Set a secret key before running the server (or copy `.env.example` to `.env` and edit):

```bash
export SECRET_KEY=$(python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY)
```

### Web Interface (Recommended)

1. **Install Dependencies:**
   ```bash
   pip install flask pypdf
   ```

2. **Start the Server:**
   ```bash
   python run.py
   ```

3. **Open in Browser:**
   Navigate to `http://127.0.0.1:5000`

4. **Upload & Convert:**
   - Drag and drop your PDF/TXT file
   - Click "Generate Smart Notes"
   - Download the converted HTML file

### Command Line

```bash
python converter/pdf_to_html.py your_notes.pdf
```

Output will be saved as `Generated_Smart_Notes.html`

## 📁 Project Structure

```
calculus/
├── app/                        # Flask web application
│   ├── app.py                  # Main Flask app
│   ├── templates/              # HTML templates
│   │   └── index.html         # Upload interface
│   └── static/                # Static assets (empty)
├── converter/                  # Conversion logic
│   ├── pdf_to_html.py         # Main conversion script
│   ├── smart_template.html    # HTML template with styles
│   └── __init__.py
├── examples/                   # Example outputs
│   ├── Calculus1 smart notes.html  # Syllabus-aligned notes
│   ├── Calculus AI.html
│   └── Generated_Smart_Notes.html
├── data/                       # Source files
│   ├── sma103_text.txt
│   └── 0programming paradigms.pdf
├── tests/                      # Test files
│   └── test_app.py
├── uploads/                    # Temporary uploads
├── outputs/                    # Generated outputs
├── run.py                      # Main entry point
├── .gitignore
└── README.md
```

## 🎯 How It Works

1. **Text Extraction**: Uses `pypdf` to extract text from PDF files
2. **Smart Parsing**: Regex patterns detect:
   - Chapter/Unit headings → Creates tabs
   - "Definition:" → Wraps in blue accent box
   - "Theorem:" → Wraps in yellow accent box
   - "Example:" → Wraps in styled example box
3. **Template Injection**: Injects formatted content into glassmorphism template
4. **Output**: Generates fully interactive HTML file

## 🎨 Customization

### Modify Colors
Edit CSS variables in `smart_template.html`:
```css
:root {
    --accent: #38bdf8;        /* Primary accent color */
    --warning: #eab308;       /* Theorem boxes */
    --success: #22c55e;       /* Success states */
}
```

### Add Detection Patterns
Edit regex patterns in `pdf_to_html.py`:
```python
def_pattern = re.compile(r'^\s*(Definition|Define)\b[:\.]?(.*)', re.IGNORECASE)
```

## 🔧 Requirements

- Python 3.7+
- `pypdf` (PDF text extraction)
- `flask` (Web interface)

## 📝 Example Usage

### Converting Course Notes
```bash
python pdf_to_html.py "Linear Algebra Notes.pdf"
```

### Batch Processing
```bash
for file in *.pdf; do
    python pdf_to_html.py "$file"
done
```

## 🌐 Deployment

For production deployment, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## 📄 License

Created by @mr-ceo7 (GitHub username from git config)

## 🤝 Contributing

Feel free to fork, modify, and improve! This project was designed to make studying more interactive and enjoyable.

---

**Pro Tip**: The web interface is perfect for one-off conversions, while the command line script is ideal for batch processing multiple files.
