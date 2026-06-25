"""
ZICore System Installer
Installs all dependencies and sets up the environment
"""
import subprocess
import sys
import os
from pathlib import Path

BANNER = """
===============================================
  ZICORE AEROSYSTEM INSTALLER v0.3.0
  Dual-Engine Inference | Multimedia Agent
===============================================
"""

CORE_DEPS = [
    "fastapi",
    "uvicorn[standard]",
    "websockets",
    "pydantic",
    "requests",
]

TEST_DEPS = [
    "pytest",
    "pytest-asyncio",
    "httpx",
]

AGENT_DEPS = [
    "Pillow",
    "numpy",
    "pyttsx3",
]

VOICE_DEPS = [
    "openai-whisper",
    "pyaudio",
]

THREE_D_DEPS = [
    "trimesh",
]

ML_DEPS = [
    "torch",
    "transformers",
]


def run(cmd, description=""):
    print(f"  Installing {description}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"    [OK] {description}")
        return True
    else:
        print(f"    [FAIL] {description}")
        if result.stderr:
            print(f"    Error: {result.stderr[:200]}")
        return False


def main():
    print(BANNER)

    print("  Step 1/6: Core dependencies")
    for dep in CORE_DEPS:
        run([sys.executable, "-m", "pip", "install", dep, "-q"], dep)

    print("\n  Step 2/6: Test dependencies")
    for dep in TEST_DEPS:
        run([sys.executable, "-m", "pip", "install", dep, "-q"], dep)

    print("\n  Step 3/6: Agent dependencies (media)")
    for dep in AGENT_DEPS:
        run([sys.executable, "-m", "pip", "install", dep, "-q"], dep)

    print("\n  Step 4/6: 3D mesh generation")
    for dep in THREE_D_DEPS:
        run([sys.executable, "-m", "pip", "install", dep, "-q"], dep)

    print("\n  Step 5/6: Voice engine")
    for dep in VOICE_DEPS:
        run([sys.executable, "-m", "pip", "install", dep, "-q"], dep)

    print("\n  Step 6/6: ML engine (optional, larger download)")
    install_ml = input("  Install ML engine (torch + transformers)? [y/N]: ").strip().lower()
    if install_ml == "y":
        for dep in ML_DEPS:
            run([sys.executable, "-m", "pip", "install", dep, "-q"], dep)
    else:
        print("  Skipping ML engine. Engine B will use mock mode.")

    print("\n" + "=" * 50)
    print("  INSTALLATION COMPLETE")
    print("=" * 50)
    print("\n  Run the system:")
    print("    python zicore_menu.py        # Interactive menu")
    print("    python start.py              # Quick start backend+frontend")
    print("    python -m pytest tests/ -v   # Run tests")
    print("\n  Dashboard: http://localhost:3000")
    print("  API Docs:  http://localhost:8080/docs")
    print("  Agent:     http://localhost:8080/api/infer")
    print()


if __name__ == "__main__":
    main()
