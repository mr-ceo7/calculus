#!/usr/bin/env python3
"""
Smart Notes Generator - Main Entry Point

This is the main file to run the application.
Simply run: python run.py
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from app import create_app

if __name__ == '__main__':
    # Create and run the Flask application
    app = create_app()
    print("\n" + "="*60)
    print("🚀 Smart Notes Generator")
    print("="*60)
    print("📍 Open your browser and go to: http://localhost:8000")
    print("📝 Upload a PDF or TXT file to convert it to Smart Notes")
    print("💡 Press CTRL+C to stop the server")
    print("="*60 + "\n")
    
    # Run without reloader to avoid watchdog issues
    app.run(debug=True, host='0.0.0.0', port=8000, use_reloader=False)
