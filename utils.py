# utils.py
"""Utility functions for Archopinion"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
import hashlib
from datetime import datetime

def cleanup_temp_files(temp_dir: Path):
    """Clean up temporary files older than 24 hours"""
    if not temp_dir.exists():
        return
        
    current_time = datetime.now().timestamp()
    for file in temp_dir.iterdir():
        if file.is_file():
            file_age = current_time - file.stat().st_mtime
            if file_age > 86400:  # 24 hours
                file.unlink()

def validate_pdf(file_path: Path) -> bool:
    """Validate if file is a valid PDF"""
    if not file_path.exists():
        return False
        
    # Check file extension
    if not file_path.suffix.lower() == '.pdf':
        return False
        
    # Check PDF header
    with open(file_path, 'rb') as f:
        header = f.read(4)
        return header == b'%PDF'

def get_file_hash(file_path: Path) -> str:
    """Generate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    
    return name + ext