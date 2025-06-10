# test_cli.py
"""Test script for Archopinion CLI"""

import os
import sys
from pathlib import Path

# Set up test environment
os.environ['GEMINI_API_KEY'] = 'test_key_123'

from models import ProjectInfo, UploadedDocument, AnalysisRequest
from datetime import datetime

def test_models():
    """Test data models"""
    print("Testing data models...")
    
    # Test ProjectInfo
    project = ProjectInfo(
        address="123 Test Street, London",
        project_type="Residential - Extension (Rear)",
        council="London Borough of Test",
        planning_reference="TEST/2024/001"
    )
    print(f"✓ ProjectInfo created: {project.address}")
    
    # Test UploadedDocument
    doc = UploadedDocument(
        file_path=Path("test.pdf"),
        document_type="Site Plan",
        file_uri="gs://test/file.pdf"
    )
    print(f"✓ UploadedDocument created: {doc.document_type}")
    
    # Test AnalysisRequest
    request = AnalysisRequest(
        project_info=project,
        documents=[doc],
        selected_frameworks=["NPPF", "PDR"],
        user_prompt="Test analysis"
    )
    print(f"✓ AnalysisRequest created at: {request.created_at}")
    
    print("\nAll model tests passed!")

def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    from config import Config
    
    print(f"✓ API Key configured: {'***' + Config.GEMINI_API_KEY[-4:] if Config.GEMINI_API_KEY else 'Not set'}")
    print(f"✓ Output directory: {Config.OUTPUT_DIR}")
    print(f"✓ Temp directory: {Config.TEMP_DIR}")
    print(f"✓ Frameworks available: {len(Config.PLANNING_FRAMEWORKS)}")
    print(f"✓ Project types available: {len(Config.PROJECT_TYPES)}")
    
def test_utils():
    """Test utility functions"""
    print("\nTesting utilities...")
    from utils import format_file_size, sanitize_filename
    
    # Test file size formatting
    assert format_file_size(1234) == "1.2 KB"
    assert format_file_size(1234567) == "1.2 MB"
    print("✓ File size formatting works")
    
    # Test filename sanitization
    assert sanitize_filename("test<>file?.pdf") == "test__file_.pdf"
    print("✓ Filename sanitization works")

if __name__ == "__main__":
    print("Running Archopinion tests...\n")
    
    test_models()
    test_config()
    test_utils()
    
    print("\n✅ All tests completed!")