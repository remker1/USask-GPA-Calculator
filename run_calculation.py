import subprocess
import sys
import os

# Install pymupdf if not already available
try:
    import fitz
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])

# Install PySide6 (Qt for Python) if not already available
try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PySide6"])

# Run the main calculation app
script_path = os.path.join(os.path.dirname(__file__), "calculation.py")
subprocess.run([sys.executable, script_path])
