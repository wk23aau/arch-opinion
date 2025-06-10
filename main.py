# main.py
#!/usr/bin/env python3
"""
Archopinion - AI Architectural Review Platform
Main entry point for the command-line application
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main

if __name__ == "__main__":
    main()