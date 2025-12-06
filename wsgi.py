#!/usr/bin/env python3
"""
WSGI entry point for production deployment on Render
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
