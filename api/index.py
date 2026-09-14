import sys
import os

# Ensure the project root directory is accessible on Python's path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import app
