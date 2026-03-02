"""
Centralized configuration for paths and system constants.
"""

import os
from pathlib import Path

# This file is located at root/backend/config.py
BACKEND_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = BACKEND_DIR.parent.resolve()

# Root-level directories
VECTOR_EMBEDDING_STORAGE_DIR = PROJECT_ROOT / "vector_embedding_storage"
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"

# Ensure core directories exist
for directory in [VECTOR_EMBEDDING_STORAGE_DIR, UPLOADS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
