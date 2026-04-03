"""
Wavelet Image Search Engine
Core module: wavelet hashing, Hamming distance, and image database management.
Extended from Lab 4 implementation.
"""

import numpy as np
import cv2
import pywt
import os
import json
import io
import base64
from pathlib import Path


def wavelet_hash(image, size=(64, 64), wavelet='haar'):
    """
    Compute wavelet hash for an image using DWT.
    
    Args:
        image: BGR image (numpy array) or file path string
        size: resize target (default 64x64)
        wavelet: wavelet type (default 'haar')
    
    Returns:
        1D boolean array (the hash)
    """
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Cannot read image: {image}")
    
    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Resize and normalize
    gray = cv2.resize(gray, size)
    gray = np.float32(gray) / 255.0
    
    # Discrete Wavelet Transform (level 1)
    coeffs = pywt.wavedec2(gray, wavelet, level=1)
    LL, (LH, HL, HH) = coeffs
    
    # Create hash from LL subband
    avg = np.mean(LL)
    diff = LL > avg
    
    return diff.flatten()


def hamming_distance(hash1, hash2):
    """
    Compute Hamming distance between two hashes.
    
    Args:
        hash1, hash2: 1D boolean arrays
    
    Returns:
        int: number of differing bits
    """
    return int(np.count_nonzero(hash1 != hash2))


def get_wavelet_visualization(image, size=(256, 256), wavelet='haar'):
    """
    Generate wavelet decomposition visualization (LL, LH, HL, HH subbands).
    
    Args:
        image: BGR image (numpy array) or file path
        size: resize target
        wavelet: wavelet type
    
    Returns:
        PNG image bytes (base64 encoded string)
    """
    if isinstance(image, str):
        image = cv2.imread(image)
    
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    gray = cv2.resize(gray, size)
    gray = np.float32(gray) / 255.0
    
    coeffs = pywt.wavedec2(gray, wavelet, level=1)
    LL, (LH, HL, HH) = coeffs
    
    # Normalize each subband for visualization
    def normalize(arr):
        mn, mx = arr.min(), arr.max()
        if mx - mn == 0:
            return np.zeros_like(arr, dtype=np.uint8)
        return ((arr - mn) / (mx - mn) * 255).astype(np.uint8)
    
    ll_img = normalize(LL)
    lh_img = normalize(LH)
    hl_img = normalize(HL)
    hh_img = normalize(HH)
    
    # Combine into 2x2 grid
    h, w = ll_img.shape
    canvas = np.zeros((h * 2 + 4, w * 2 + 4), dtype=np.uint8)
    canvas[0:h, 0:w] = ll_img
    canvas[0:h, w+4:w*2+4] = lh_img
    canvas[h+4:h*2+4, 0:w] = hl_img
    canvas[h+4:h*2+4, w+4:w*2+4] = hh_img
    
    # Apply colormap for better visualization
    colored = cv2.applyColorMap(canvas, cv2.COLORMAP_VIRIDIS)
    
    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(colored, 'LL', (10, 25), font, 0.7, (255, 255, 255), 2)
    cv2.putText(colored, 'LH', (w + 14, 25), font, 0.7, (255, 255, 255), 2)
    cv2.putText(colored, 'HL', (10, h + 29), font, 0.7, (255, 255, 255), 2)
    cv2.putText(colored, 'HH', (w + 14, h + 29), font, 0.7, (255, 255, 255), 2)
    
    _, buffer = cv2.imencode('.png', colored)
    return base64.b64encode(buffer).decode('utf-8')


class ImageDatabase:
    """
    In-memory image database with wavelet hash indexing.
    """
    
    def __init__(self, db_dir=None):
        self.images = {}  # filename -> { path, hash, category }
        self.db_dir = db_dir
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def add_image(self, filepath, category='unknown'):
        """
        Add an image to the database.
        
        Args:
            filepath: path to image file
            category: optional category label
        
        Returns:
            filename (key in database)
        """
        filepath = str(filepath)
        img = cv2.imread(filepath)
        if img is None:
            raise ValueError(f"Cannot read image: {filepath}")
        
        h = wavelet_hash(img)
        filename = os.path.basename(filepath)
        
        self.images[filename] = {
            'path': os.path.abspath(filepath),
            'hash': h,
            'category': category,
            'hash_size': len(h)
        }
        
        return filename
    
    def index_directory(self, directory, category='unknown'):
        """
        Index all images in a directory.
        
        Args:
            directory: path to directory
            category: category label for all images
        
        Returns:
            number of indexed images
        """
        count = 0
        extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}
        
        for f in os.listdir(directory):
            ext = os.path.splitext(f)[1].lower()
            if ext in extensions:
                try:
                    self.add_image(os.path.join(directory, f), category=category)
                    count += 1
                except Exception as e:
                    print(f"Warning: Could not index {f}: {e}")
        
        return count
    
    def search(self, query_image, top_k=10, threshold=None):
        """
        Search for similar images.
        
        Args:
            query_image: BGR image (numpy array) or file path
            top_k: number of results to return
            threshold: optional max Hamming distance threshold
        
        Returns:
            list of { filename, path, distance, similarity, category }
        """
        if isinstance(query_image, str):
            img = cv2.imread(query_image)
        else:
            img = query_image
        
        if img is None:
            return []
        
        query_hash = wavelet_hash(img)
        hash_len = len(query_hash)
        
        results = []
        for filename, data in self.images.items():
            dist = hamming_distance(query_hash, data['hash'])
            similarity = 1.0 - (dist / hash_len) if hash_len > 0 else 0.0
            
            if threshold is not None and dist > threshold:
                continue
            
            results.append({
                'filename': filename,
                'path': data['path'],
                'distance': dist,
                'similarity': round(similarity * 100, 2),
                'category': data['category']
            })
        
        # Sort by distance (ascending)
        results.sort(key=lambda x: x['distance'])
        
        return results[:top_k]
    
    def get_all_images(self):
        """Get list of all images in database."""
        return [
            {
                'filename': fname,
                'path': data['path'],
                'category': data['category']
            }
            for fname, data in self.images.items()
        ]
    
    def get_image_count(self):
        """Get total number of images in database."""
        return len(self.images)
    
    def save_uploaded_image(self, file_storage, filename):
        """
        Save an uploaded image to the database directory and index it.
        
        Args:
            file_storage: Flask FileStorage object
            filename: desired filename
        
        Returns:
            filename used
        """
        if self.db_dir is None:
            raise ValueError("No database directory configured")
        
        save_path = os.path.join(self.db_dir, filename)
        file_storage.save(save_path)
        self.add_image(save_path, category='uploaded')
        
        return filename
