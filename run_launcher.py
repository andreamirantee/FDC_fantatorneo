"""Launcher EXE: avvia il server usando il `python` disponibile in PATH.
Questo EXE non include FastAPI/uvicorn: usa il Python di sistema.
"""
import subprocess
import sys
import os

def main():
    # Determine project directory (the directory where this launcher lives)
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Prefer project virtualenv if present (look relative to project dir)
    venv_python = os.path.join(project_dir, '.venv', 'Scripts', 'python.exe')
    python_cmd = 'python'
    if os.path.exists(venv_python):
        python_cmd = venv_python

    cmd = [python_cmd, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
    try:
        print("Starting server with:", " ".join(cmd))
        # Use project_dir as working directory so .env next to the exe is loaded
        proc = subprocess.Popen(cmd, cwd=project_dir)
        proc.wait()
    except KeyboardInterrupt:
        print("Stopping server")
    except Exception as e:
        print("Launcher error:", e)
        sys.exit(1)

if __name__ == '__main__':
    main()
