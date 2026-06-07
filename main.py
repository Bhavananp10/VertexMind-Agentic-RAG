"""
VertexMind – Agentic Enterprise Knowledge Assistant
Root launcher: starts the FastAPI backend from the backend/ directory.

Usage:
    python main.py
    # or via uv:
    uv run main.py
"""

import subprocess
import sys
import os


def main():
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")

    print("=" * 60)
    print("  VertexMind – Agentic Enterprise Knowledge Assistant")
    print("=" * 60)
    print(f"  Backend dir : {backend_dir}")
    print(f"  Server URL  : http://localhost:8000")
    print(f"  Frontend    : http://localhost:5173  (run: npm run dev)")
    print("=" * 60)
    print("  Press Ctrl+C to stop the server.")
    print("=" * 60 + "\n")

    try:
        subprocess.run(
            [sys.executable, "main.py"],
            cwd=backend_dir,
            check=True,
        )
    except KeyboardInterrupt:
        print("\n  Server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"\n  Backend exited with code {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
