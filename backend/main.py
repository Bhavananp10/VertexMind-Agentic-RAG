"""
VertexMind backend entry point.

Automatically uses the local .venv if present,
so you do NOT need to manually activate it.

Run:  python main.py
"""

import subprocess
import sys
import os


def main():
    backend_dir = os.path.dirname(os.path.abspath(__file__))

    # Prefer the venv uvicorn so all backend packages are visible
    venv_uvicorn = os.path.join(backend_dir, ".venv", "Scripts", "uvicorn.exe")

    if os.path.exists(venv_uvicorn):
        cmd = [venv_uvicorn, "app:app",
               "--host", "0.0.0.0",
               "--port", "8000",
               "--reload"]
    else:
        # Fallback: use whatever python is active
        cmd = [sys.executable, "-m", "uvicorn", "app:app",
               "--host", "0.0.0.0",
               "--port", "8000",
               "--reload"]

    print("=" * 55)
    print("  VertexMind – Backend API Server")
    print("  http://localhost:8000")
    print("=" * 55)

    subprocess.run(cmd, cwd=backend_dir)


if __name__ == "__main__":
    main()
