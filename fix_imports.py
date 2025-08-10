#\!/usr/bin/env python3
"""
Fix import sorting issues
"""

import subprocess
import sys

files = [
    "src/api/config.py",
    "src/api/exceptions/custom_exceptions.py",
    "src/api/schemas/auth.py",
    "src/api/schemas/common.py",
    "src/api/schemas/prediction.py",
    "src/api/websocket/connection_manager.py",
]

for file in files:
    print(f"Fixing imports in {file}")
    # Use isort to fix imports
    subprocess.run(["python", "-m", "isort", file, "--profile", "black"], capture_output=True)

print("Done\!")
