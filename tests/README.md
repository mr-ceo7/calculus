# Test Suite

This folder contains all the automated tests for the Smart Notes Generator.

## What Are Tests?

Tests are code that checks if the application works correctly. Think of them like a checklist that runs automatically!

## Test Files

### 🧪 conftest.py
**What it does:** Sets up reusable test utilities and sample data.

Contains "fixtures" - pre-made test files and settings that all tests can use.

### 📦 test_converter.py (18 tests)
**What it tests:** The PDF to HTML conversion logic

Tests things like:
- Does it detect definitions correctly?
- Does it find theorems and examples?
- Does it split chapters into tabs?
- Does it handle errors gracefully?

### 🔧 test_utils.py (16 tests)
**What it tests:** Helper functions

Tests things like:
- File validation
- Filename sanitization  
- Path handling
- Safety checks

### 🌐 test_routes.py (11 tests)
**What it tests:** Web interface and file uploads

Tests things like:
- Does the homepage load?
- Can files be uploaded?
- Are invalid files rejected?
- Does file cleanup work?

### 📜 test_app.py
Legacy test file (older style) - kept for reference.

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Tests
```bash
# Just converter tests
pytest tests/test_converter.py

# Just utility tests
pytest tests/test_utils.py

# Just web interface tests
pytest tests/test_routes.py
```

### Verbose Output
```bash
pytest -v
```

## Why Tests Matter

✅ **Confidence** - Know that changes don't break things
✅ **Documentation** - Tests show how code should work  
✅ **Quality** - Catch bugs before users do
✅ **Speed** - Automated checking is faster than manual

## Current Status

**47 tests passing** ✅

All core functionality is verified and working!
