#!/usr/bin/env python3
"""
Smart Notes Generator - Main Runner
Starts the Flask web application
"""

import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
