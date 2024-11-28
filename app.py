import logging
from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
from functools import wraps
from dotenv import load_dotenv
import fitz  # type: ignore
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB
API_KEY = os.getenv('API_KEY', 'default-key')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize the limiter
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per day", "50 per hour"]  # Global rate limits
)

# Authentication
def require_api_key(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('Authorization')
        if not provided_key or provided_key != f"Bearer {API_KEY}":
            logging.warning("Unauthorized access attempt.")
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return decorated_function

# Error handlers
@app.errorhandler(404)
def not_found_error(e):
    logging.error("Endpoint not found.")
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logging.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.errorhandler(413)
def file_too_large(e):
    logging.error("File too large.")
    return jsonify({"error": "File too large"}), 413

# Text extraction function (HTML)
def extract_html_from_pdf(filepath):
    html_content = ""
    try:
        with fitz.open(filepath) as doc:
            for page in doc:
                html_content += page.get_text("blocks")  # Extract page HTML
        return html_content
    except Exception as e:
        logging.error(f"Error extracting HTML from PDF: {e}")
        raise RuntimeError(f"Error extracting HTML from PDF: {e}")

# Text extraction function (standard text)
def extract_text_from_pdf(filepath):
    text_content = ""
    try:
        with fitz.open(filepath) as doc:
            for page in doc:
                text_content += page.get_text("text")  # Extract plain text
        return text_content
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        raise RuntimeError(f"Error extracting text from PDF: {e}")

# Endpoint for HTML extraction
@limiter.limit("10 per minute")  # Rate limit for this endpoint
@app.route('/pdf-to-html', methods=['POST'])
@require_api_key
def pdf_to_html():
    if 'file' not in request.files:
        logging.warning("No file provided in the request.")
        return jsonify({"status": "error", "message": "No file provided", "code": 400}), 400

    file = request.files['file']
    if file.filename == '':
        logging.warning("No file selected.")
        return jsonify({"status": "error", "message": "No file selected", "code": 400}), 400

    filename = secure_filename(file.filename)
    if not filename.lower().endswith('.pdf'):
        logging.warning(f"Invalid file type uploaded: {filename}")
        return jsonify({"status": "error", "message": "Invalid file type. Only PDF files are allowed.", "code": 400}), 400

    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logging.info(f"File saved at: {filepath}")

        # HTML extraction
        html_content = extract_html_from_pdf(filepath)
        os.remove(filepath)
        logging.info(f"File processed and deleted: {filepath}")

        return jsonify({
            "status": "success",
            "data": {
                "filename": filename,
                "html": html_content
            },
            "message": "HTML successfully extracted."
        }), 200
    except RuntimeError as e:
        logging.error(f"Runtime error during HTML extraction: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "code": 400
        }), 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred.",
            "details": str(e),
            "code": 500
        }), 500

# Endpoint for text extraction
@limiter.limit("50 per minute")  # Rate limit for this endpoint
@app.route('/pdf-to-text', methods=['POST'])
@require_api_key
def pdf_to_text():
    if 'file' not in request.files:
        logging.warning("No file provided in the request.")
        return jsonify({"status": "error", "message": "No file provided", "code": 400}), 400

    file = request.files['file']
    if file.filename == '':
        logging.warning("No file selected.")
        return jsonify({"status": "error", "message": "No file selected", "code": 400}), 400

    filename = secure_filename(file.filename)
    if not filename.lower().endswith('.pdf'):
        logging.warning(f"Invalid file type uploaded: {filename}")
        return jsonify({"status": "error", "message": "Invalid file type. Only PDF files are allowed.", "code": 400}), 400

    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logging.info(f"File saved at: {filepath}")

        # Text extraction
        text_content = extract_text_from_pdf(filepath)
        os.remove(filepath)
        logging.info(f"File processed and deleted: {filepath}")

        return jsonify({
            "status": "success",
            "data": {
                "filename": filename,
                "text": text_content
            },
            "message": "Text successfully extracted."
        }), 200
    except RuntimeError as e:
        logging.error(f"Runtime error during text extraction: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "code": 400
        }), 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred.",
            "details": str(e),
            "code": 500
        }), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)