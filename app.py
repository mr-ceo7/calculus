from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
from werkzeug.utils import secure_filename
from pdf_to_html import generate_smart_notes, parse_pdf
import tempfile

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Generate output filename
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_smart_notes.html"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        try:
            # Convert the file
            if filename.lower().endswith('.pdf'):
                generate_smart_notes(filepath, output_path)
            elif filename.lower().endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                generate_smart_notes(filepath, output_path, text_content=text)
            
            flash('File converted successfully!', 'success')
            return send_file(output_path, as_attachment=True, download_name=output_filename)
        
        except Exception as e:
            flash(f'Error converting file: {str(e)}', 'error')
            return redirect(url_for('index'))
        
        finally:
            # Cleanup uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    else:
        flash('Invalid file type. Please upload PDF or TXT files only.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
