# Application Source Code

This folder contains all the application code for the Smart Notes Generator.

## Structure

```
src/
├── app.py              # Main Flask application (start here!)
├── routes.py           # Web page handlers (what happens when you visit URLs)
├── config.py           # Settings and configuration
├── converter/          # PDF to HTML conversion logic
│   ├── pdf_to_html.py    # Main conversion code
│   ├── exceptions.py     # Custom error types
│   ├── utils.py          # Helper functions
│   └── smart_template.html  # HTML template for output
└── templates/          # Web interface templates
    └── index.html        # Upload page
```

## What Each File Does

### 🚀 app.py
The main application file. Creates the Flask web server and sets everything up.

### 🛣️ routes.py  
Defines what happens when users visit different URLs (like the homepage or upload page).

### ⚙️ config.py
Contains all the settings like file size limits, folder locations, etc.

### 📁 converter/
The folder with all the PDF conversion logic:
- **pdf_to_html.py** - Reads PDFs and converts them to beautiful HTML
- **exceptions.py** - Special error messages for when things go wrong
- **utils.py** - Helper functions for file handling
- **smart_template.html** - The pretty HTML template used for output

### 🎨 templates/
HTML templates for the web interface
- **index.html** - The upload page where users drag & drop files

## How It Works

1. **run.py** starts the app
2. **app.py** creates the Flask server
3. **routes.py** handles user requests
4. **converter/** does the PDF to HTML magic
5. **templates/** provides the web interface

## For Developers

- All imports use relative paths (from src folder)
- Type hints are used throughout for clarity
- Logging is configured for debugging
- Tests are in the `tests/` folder at project root
