import fitz
from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
from functools import wraps
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile
import mimetypes

# Lade Environment-Variablen
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB
API_KEY = os.getenv('API_KEY', 'default-key')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Authentifizierung
def require_api_key(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('Authorization')
        if not provided_key or provided_key != f"Bearer {API_KEY}":
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return decorated_function

# Fehlerhandler
@app.errorhandler(404)
def not_found_error(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File too large"}), 413

# Text-Extraktionsfunktion (HTML)
def extract_html_from_pdf(filepath):
    html_content = ""
    try:
        with fitz.open(filepath) as doc:
            for page in doc:
                html_content += page.get_text("html")  # Extrahiere HTML der Seite
        return html_content
    except Exception as e:
        raise RuntimeError(f"Error extracting HTML from PDF: {e}")

# Text-Extraktionsfunktion (Standardtext)
def extract_text_from_pdf(filepath):
    text_content = ""
    try:
        with fitz.open(filepath) as doc:
            for page in doc:
                text_content += page.get_text("text")  # Extrahiere normalen Text
        return text_content
    except Exception as e:
        raise RuntimeError(f"Error extracting text from PDF: {e}")

# Endpunkt für HTML-Extraktion
@app.route('/pdf-to-html', methods=['POST'])
@require_api_key
def pdf_to_html():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided", "code": 400}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected", "code": 400}), 400

    try:
        with NamedTemporaryFile(delete=True, suffix='.pdf') as temp_file:
            file.save(temp_file.name)

            # MIME-Typ überprüfen
            mime_type, _ = mimetypes.guess_type(temp_file.name)
            if mime_type != 'application/pdf':
                return jsonify({"status": "error", "message": "File is not a valid PDF", "code": 400}), 400

            # HTML-Extraktion
            html_content = extract_html_from_pdf(temp_file.name)

        return jsonify({
            "status": "success",
            "data": {
                "filename": file.filename,
                "html": html_content
            },
            "message": "HTML successfully extracted."
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Failed to process PDF.",
            "details": "An internal error occurred.",
            "code": 500
        }), 500

# Endpunkt für Text-Extraktion
@app.route('/pdf-to-text', methods=['POST'])
@require_api_key
def pdf_to_text():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided", "code": 400}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected", "code": 400}), 400

    try:
        with NamedTemporaryFile(delete=True, suffix='.pdf') as temp_file:
            file.save(temp_file.name)

            # MIME-Typ überprüfen
            mime_type, _ = mimetypes.guess_type(temp_file.name)
            if mime_type != 'application/pdf':
                return jsonify({"status": "error", "message": "File is not a valid PDF", "code": 400}), 400

            # Text-Extraktion
            text_content = extract_text_from_pdf(temp_file.name)

        return jsonify({
            "status": "success",
            "data": {
                "filename": file.filename,
                "text": text_content
            },
            "message": "Text successfully extracted."
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Failed to process PDF.",
            "details": "An internal error occurred.",
            "code": 500
        }), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
