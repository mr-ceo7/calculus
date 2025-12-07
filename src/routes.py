"""
Main routes blueprint for Smart Notes Generator
Handles file upload and conversion endpoints
"""
import os
import logging
from pathlib import Path
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

# Import converter modules
from converter.pdf_to_html import generate_smart_notes, parse_pdf
from converter.exceptions import ConversionError
from converter.ai_converter import generate_ai_notes, GeminiUnavailable

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('main', __name__)


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


@bp.route('/')
def index():
    """Render the upload page"""
    from flask import current_app
    return render_template('index.html', ai_enabled=current_app.config.get('GEMINI_ENABLED', False))


@bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and conversion"""
    from flask import current_app
    
    # Validate file in request
    if 'file' not in request.files:
        from flask import jsonify
        return jsonify({'success': False, 'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        from flask import jsonify
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    # Validate file extension
    if not file or not allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        from flask import jsonify
        return jsonify({'success': False, 'error': 'Invalid file type. Please upload PDF or TXT files only.'}), 400
    
    # Secure the filename
    filename = secure_filename(file.filename)
    upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
    output_folder = Path(current_app.config['OUTPUT_FOLDER'])
    
    filepath = upload_folder / filename
    output_filename = f"{filepath.stem}_smart_notes.html"
    output_path = output_folder / output_filename

    mode = request.form.get('mode', 'standard').lower()
    use_ai_requested = mode == 'gemini'
    ai_attempted = False
    ai_failed = False
    
    try:
        # Save uploaded file
        file.save(str(filepath))
        logger.info(f"Processing uploaded file: {filename}")
        
        text_content = None
        if filename.lower().endswith('.pdf'):
            text_content = parse_pdf(filepath)
        elif filename.lower().endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()

        if use_ai_requested and current_app.config.get('GEMINI_ENABLED'):
            try:
                ai_attempted = True
                generate_ai_notes(
                    text_content=text_content,
                    output_path=output_path,
                    template_path=current_app.config['TEMPLATE_PATH'],
                    api_key=current_app.config['GEMINI_API_KEY'],
                    preferred_model=current_app.config['GEMINI_PREFERRED_MODEL'],
                    fallback_model=current_app.config['GEMINI_FALLBACK_MODEL'],
                    timeout_seconds=current_app.config['GEMINI_TIMEOUT_SECONDS'],
                    max_chars=current_app.config['GEMINI_MAX_CHARS'],
                    max_chunk_words=current_app.config['GEMINI_MAX_CHUNK_WORDS'],
                )
            except (GeminiUnavailable, Exception) as e:  # noqa: BLE001
                ai_failed = True
                logger.warning(f"Gemini generation failed, falling back: {e}")
                generate_smart_notes(
                    filepath,
                    output_path,
                    template_path=current_app.config['TEMPLATE_PATH'],
                    text_content=text_content,
                )
        else:
                generate_smart_notes(
                    filepath,
                    output_path,
                    template_path=current_app.config['TEMPLATE_PATH'],
                    text_content=text_content,
                )
        
        logger.info(f"Successfully converted {filename} to {output_filename}")
        
        # Return JSON response for AJAX handling
        from flask import jsonify
        return jsonify({
            'success': True,
            'filename': output_filename,
            'original_name': filename,
            'preview_url': url_for('main.preview_file', filename=output_filename),
            'download_url': url_for('main.download_file', filename=output_filename),
            'ai_used': ai_attempted and not ai_failed,
            'ai_fallback': ai_failed,
            'ai_enabled': current_app.config.get('GEMINI_ENABLED', False)
        })
    
    except ConversionError as e:
        logger.error(f"Conversion error: {e}")
        from flask import jsonify
        return jsonify({'success': False, 'error': f'Error converting file: {e.message}'}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error during conversion: {e}", exc_info=True)
        from flask import jsonify
        return jsonify({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}), 500
    
    finally:
        # Cleanup uploaded file
        if filepath.exists():
            try:
                filepath.unlink()
                logger.debug(f"Cleaned up uploaded file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to cleanup uploaded file: {e}")


@bp.route('/download/<filename>')
def download_file(filename):
    """Download the generated HTML file"""
    from flask import current_app, abort
    
    try:
        output_folder = Path(current_app.config['OUTPUT_FOLDER'])
        file_path = output_folder / filename
        
        # Security: ensure file exists and is in output folder
        if not file_path.exists() or not str(file_path).startswith(str(output_folder)):
            abort(404)
        
        logger.info(f"Downloading file: {filename}")
        return send_file(file_path, as_attachment=True, download_name=filename)
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        abort(404)


@bp.route('/preview/<filename>')
def preview_file(filename):
    """Preview the generated HTML file in browser"""
    from flask import current_app, abort
    
    try:
        output_folder = Path(current_app.config['OUTPUT_FOLDER'])
        file_path = output_folder / filename
        
        # Security: ensure file exists and is in output folder
        if not file_path.exists() or not str(file_path).startswith(str(output_folder)):
            abort(404)
        
        logger.info(f"Previewing file: {filename}")
        return send_file(file_path, mimetype='text/html')
    
    except Exception as e:
        logger.error(f"Preview error: {e}")
        abort(404)
