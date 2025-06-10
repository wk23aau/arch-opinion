# config.py
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', './reports'))
    TEMP_DIR = Path(os.getenv('TEMP_DIR', './temp'))
    
    # Create directories if they don't exist
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)
    
    # UK Planning Authorities and Frameworks
    PLANNING_FRAMEWORKS = {
        "NPPF": "National Planning Policy Framework",
        "PPG": "Planning Practice Guidance", 
        "PDR": "Permitted Development Rights",
        "LDF": "Local Development Framework",
        "LP": "London Plan (Greater London only)",
        "BRE": "Building Regulations",
        "SPD": "Supplementary Planning Documents"
    }
    
    PROJECT_TYPES = [
        "Residential - New Build",
        "Residential - Extension (Rear)",
        "Residential - Extension (Side)",
        "Residential - Loft Conversion",
        "Residential - Renovation",
        "Commercial - New Build",
        "Commercial - Change of Use",
        "Mixed Use Development"
    ]
    
    DOCUMENT_TYPES = [
        "Site Plan",
        "Floor Plans - Existing",
        "Floor Plans - Proposed",
        "Elevations - Existing", 
        "Elevations - Proposed",
        "Sections",
        "Design & Access Statement",
        "Planning Statement",
        "Other Supporting Documents"
    ]