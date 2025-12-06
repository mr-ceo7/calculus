# Smart Notes Generator - Backend Architecture

## Application Structure

```
calculus/
├── app.py                          # Flask app factory (refactored)
├── routes.py                       # Main routes blueprint
├── config.py                       # Configuration system
├── converter/
│   ├── pdf_to_html.py             # Conversion logic (improved)
│   ├── exceptions.py              # Custom exceptions
│   ├── utils.py                   # Utility functions
│   └── smart_template.html        # HTML template
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── test_converter.py          # Converter unit tests
│   ├── test_utils.py              # Utility unit tests
│   └── test_routes.py             # Integration tests
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Development dependencies
└── pytest.ini                      # Test configuration
```

## Architecture Patterns

### Application Factory Pattern

```python
from app import create_app

# Create app with specific config
app = create_app('production')

# Or for testing
test_app = create_app('testing')
```

### Blueprint Organization

Routes are organized in `routes.py` blueprint:
- Cleaner code organization
- Reusable across multiple apps
- Easier to test in isolation

### Configuration Management

```python
from config import get_config

# Get environment-specific config
config = get_config('development')  # or 'production', 'testing'
```

## Running the Application

### Development Mode

```bash
export FLASK_ENV=development
python run.py
```

### Production Mode

```bash
export FLASK_ENV=production
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"
```

### Testing Mode

```bash
pytest  # Uses TestingConfig automatically
```

## Error Handling

Custom exceptions provide detailed context:

```python
try:
    generate_smart_notes(pdf_path, output_path)
except PDFParsingError as e:
    # e.filename, e.page available
    logger.error(f"Failed at page {e.page}: {e}")
except TemplateNotFoundError as e:
    # e.template_path available
    logger.error(f"Missing template: {e.template_path}")
```

## Logging

Structured logging throughout:

```python
logger.info(f"Processing file: {filename}")
logger.warning(f"Failed to cleanup: {error}")
logger.error(f"Conversion failed: {error}", exc_info=True)
```

## Key Improvements

1. **Separation of Concerns** - Config, routes, and logic separated
2. **Testability** - Application factory allows isolated testing
3. **Error Handling** - Custom exceptions with detailed context
4. **Type Safety** - Type hints throughout
5. **Logging** - Structured logging for debugging
6. **Path Handling** - Pathlib for cross-platform support
