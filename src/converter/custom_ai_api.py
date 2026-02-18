import logging
import requests
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

import os

# Ordered list of endpoints to try. Env var takes precedence.
POSSIBLE_ENDPOINTS = []
if os.environ.get('CUSTOM_AI_API_URL'):
    POSSIBLE_ENDPOINTS.append(os.environ['CUSTOM_AI_API_URL'])

POSSIBLE_ENDPOINTS.extend([
    "http://localhost:5000",
    "http://102.37.19.54:8000"
])

class CustomAPIUnavailable(Exception):
    """Raised when Custom API cannot be reached or returns an error."""
    pass

def _get_active_endpoint() -> str:
    """
    Check configured endpoints and return the first one that is reachable.
    """
    for base_url in POSSIBLE_ENDPOINTS:
        try:
            # Try a lightweight check (auth status or just root)
            # The API docs mention GET /api/auth/status, let's try that or just a simple connect
            resp = requests.get(f"{base_url}/api/auth/status", timeout=2)
            if resp.status_code in [200, 401, 403]: # Connected, even if auth required
                logger.info(f"Connected to Custom AI Gateway at {base_url}")
                return base_url
        except requests.RequestException:
            logger.debug(f"Could not connect to {base_url}")
            continue
    
    raise CustomAPIUnavailable("No Custom AI Gateway endpoints are reachable.")

def upload_file(file_path: Path) -> Dict[str, Any]:
    """
    Uploads a file to the active Custom AI Gateway with retry logic.
    """
    base_url = _get_active_endpoint()
    upload_url = f"{base_url}/api/upload"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f)}
                response = requests.post(upload_url, files=files, timeout=30)
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"Upload failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # 2s, 4s, ...
            else:
                logger.error(f"Failed to upload file to Custom API after {max_retries} attempts")
                raise CustomAPIUnavailable(f"Upload failed after retries: {e}")

def generate_completion(prompt: str, file_identifier: str) -> str:
    """
    Generate completion using the Custom AI Gateway with retry logic.
    """
    base_url = _get_active_endpoint()
    generate_url = f"{base_url}/api/generate"
    
    payload = {
        "prompt": prompt,
        "files": [file_identifier],
        "stream": False # Use non-streaming for simplicity in this fallback
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(generate_url, json=payload, timeout=600)
            response.raise_for_status()
            data = response.json()
            
            # API docs say: { "response": "..." }
            return data.get("response", "")
        except requests.RequestException as e:
            logger.warning(f"Generation failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # 5s, 10s, ...
            else:
                logger.error(f"Failed to generate completion via Custom API after {max_retries} attempts")
                raise CustomAPIUnavailable(f"Generation failed after retries: {e}")
