"""
Wavelet Image Search - Flask Web Application
"""

import os
import uuid
import base64
from pathlib import Path

import cv2
import numpy as np
from flask import (
    Flask, render_template, request, jsonify,
    send_from_directory, send_file
)
from werkzeug.utils import secure_filename

from wavelet_engine import ImageDatabase, wavelet_hash, hamming_distance, get_wavelet_visualization

# ── Configuration ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

BASE_DIR = Path(__file__).parent.resolve()
DATASET_DIR = BASE_DIR.parent / 'dataset'
SIMILAR_DIR = DATASET_DIR / 'similar'
DIFFERENT_DIR = DATASET_DIR / 'different'
UPLOAD_DIR = BASE_DIR / 'uploads'
DB_IMAGE_DIR = BASE_DIR / 'db_images'

UPLOAD_DIR.mkdir(exist_ok=True)
DB_IMAGE_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tif', 'tiff'}

# ── Initialize Database ───────────────────────────────────────────────────
db = ImageDatabase(db_dir=str(DB_IMAGE_DIR))

# Hàm khởi tạo database
def init_database():
    """Index existing dataset images on startup."""
    count = 0
    if SIMILAR_DIR.exists():
        n = db.index_directory(str(SIMILAR_DIR), category='similar')
        count += n
        print(f"  Indexed {n} images from 'similar' folder")
    if DIFFERENT_DIR.exists():
        n = db.index_directory(str(DIFFERENT_DIR), category='different')
        count += n
        print(f"  Indexed {n} images from 'different' folder")
    if DB_IMAGE_DIR.exists():
        n = db.index_directory(str(DB_IMAGE_DIR), category='uploaded')
        count += n
        print(f"  Indexed {n} uploaded images")
    print(f"  Total: {db.get_image_count()} images in database")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ─────────────────────────────────────────────────────────────────
# Route chính
@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')

# API tìm kiếm ảnh
@app.route('/api/search', methods=['POST'])
def api_search():
    """
    Search for similar images.
    Expects multipart form with 'image' file and optional 'top_k' parameter.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    top_k = request.form.get('top_k', 20, type=int)
    level = request.form.get('level', 1, type=int)
    min_similarity = request.form.get('min_similarity', 0, type=float)

    # Giới hạn level hợp lệ
    level = max(1, min(3, level))

    # Save query temporarily
    ext = file.filename.rsplit('.', 1)[1].lower()
    query_filename = f"query_{uuid.uuid4().hex[:8]}.{ext}"
    query_path = str(UPLOAD_DIR / query_filename)
    file.save(query_path)

    try:
        # Read image
        img = cv2.imread(query_path)
        if img is None:
            return jsonify({'error': 'Cannot read image'}), 400

        # Search with level and min_similarity
        results = db.search(img, top_k=top_k, level=level, min_similarity=min_similarity)

        # Generate wavelet visualization for query (theo level đã chọn)
        wavelet_viz = get_wavelet_visualization(img, level=level)

        # Compute query hash info
        q_hash = wavelet_hash(img, level=level)
        
        return jsonify({
            'query': {
                'filename': query_filename,
                'url': f'/uploads/{query_filename}',
                'wavelet_viz': wavelet_viz,
                'hash_size': len(q_hash),
                'level': level
            },
            'results': [
                {
                    'filename': r['filename'],
                    'url': get_image_url(r['filename'], r['path']),
                    'distance': r['distance'],
                    'similarity': r['similarity'],
                    'category': r['category']
                }
                for r in results
            ],
            'total_db': db.get_image_count()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API upload ảnh
@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Upload a new image to the database."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    try:
        # Create unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        safe_name = f"{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
        
        fname = db.save_uploaded_image(file, safe_name)
        
        return jsonify({
            'success': True,
            'filename': fname,
            'total_db': db.get_image_count()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API lấy danh sách ảnh trong database
@app.route('/api/images', methods=['GET'])
def api_images():
    """Get all images in database."""
    images = db.get_all_images()
    return jsonify({
        'images': [
            {
                'filename': img['filename'],
                'url': get_image_url(img['filename'], img['path']),
                'category': img['category']
            }
            for img in images
        ],
        'total': db.get_image_count()
    })

# API lấy wavelet visualization cho ảnh trong database
@app.route('/api/wavelet/<filename>', methods=['GET'])
def api_wavelet(filename):
    """Get wavelet visualization for a database image."""
    images = db.images
    if filename not in images:
        return jsonify({'error': 'Image not found'}), 404
    
    path = images[filename]['path']
    viz = get_wavelet_visualization(path)
    return jsonify({'wavelet_viz': viz, 'filename': filename})


# API serve ảnh upload
@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve uploaded query images."""
    return send_from_directory(str(UPLOAD_DIR), filename)


# API server ảnh database
@app.route('/database/<path:filename>')
def serve_database(filename):
    """Serve database images (from any indexed directory)."""
    # Search in all known directories
    for directory in [DB_IMAGE_DIR, SIMILAR_DIR, DIFFERENT_DIR]:
        filepath = directory / filename
        if filepath.exists():
            return send_from_directory(str(directory), filename)
    return "Not found", 404


# Hàm lấy URL ảnh
def get_image_url(filename, filepath):
    """Helper: resolve image URL based on its actual path."""
    filepath = str(filepath)
    if str(SIMILAR_DIR) in filepath:
        return f'/database/{filename}'
    elif str(DIFFERENT_DIR) in filepath:
        return f'/database/{filename}'
    elif str(DB_IMAGE_DIR) in filepath:
        return f'/database/{filename}'
    else:
        return f'/database/{filename}'


# ── Entry Point ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("  Wavelet Image Search Engine")
    print("=" * 60)
    print("Initializing image database...")
    init_database()
    print("=" * 60)
    print("  Server running at http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
