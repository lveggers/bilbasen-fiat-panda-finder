#!/usr/bin/env python3
"""
Environment setup script for Bilbasen Fiat Panda Finder
Handles virtual environment creation, dependency installation, and runtime directory setup.
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(command, description, check=True):
    """Run a command and handle errors."""
    print(f"[INFO] {description}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr.strip()}")
        return False


def setup_virtual_environment():
    """Create and setup virtual environment."""
    print("\n=== Setting up Python Virtual Environment ===")
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 11):
        print(f"[ERROR] Python 3.11+ required. Current: {python_version.major}.{python_version.minor}")
        return False
    
    print(f"[OK] Python {python_version.major}.{python_version.minor} detected")
    
    # Create virtual environment
    venv_path = Path("venv")
    if not venv_path.exists():
        if not run_command("python -m venv venv", "Creating virtual environment"):
            return False
    else:
        print("[INFO] Virtual environment already exists")
    
    return True


def install_dependencies(dev=False):
    """Install project dependencies."""
    print(f"\n=== Installing {'Development' if dev else 'Production'} Dependencies ===")
    
    # Determine pip command based on OS
    pip_cmd = "venv\\Scripts\\pip" if os.name == "nt" else "venv/bin/pip"
    
    # Upgrade pip first
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install dependencies
    requirements_file = "requirements-dev.txt" if dev else "requirements.txt"
    if not run_command(f"{pip_cmd} install -r {requirements_file}", f"Installing from {requirements_file}"):
        return False
    
    # Install playwright browsers if in dev mode
    if dev:
        playwright_cmd = "venv\\Scripts\\playwright" if os.name == "nt" else "venv/bin/playwright"
        run_command(f"{playwright_cmd} install", "Installing Playwright browsers")
    
    return True


def setup_runtime_directories():
    """Create runtime directory structure."""
    print("\n=== Setting up Runtime Directories ===")
    
    dirs = [
        "runtime",
        "runtime/data", 
        "runtime/fixtures",
        "runtime/logs",
        "runtime/cache",
        "runtime/temp"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"[OK] Created {dir_path}")
    
    return True


def setup_git_hooks():
    """Set up pre-commit hooks if available."""
    print("\n=== Setting up Git Hooks ===")
    
    if Path(".pre-commit-config.yaml").exists():
        pre_commit_cmd = "venv\\Scripts\\pre-commit" if os.name == "nt" else "venv/bin/pre-commit"
        if run_command(f"{pre_commit_cmd} install", "Installing pre-commit hooks", check=False):
            print("[OK] Pre-commit hooks installed")
        else:
            print("[WARN] Pre-commit hooks setup failed (optional)")
    else:
        print("[INFO] No pre-commit config found")
    
    return True


def main():
    """Main setup function."""
    print("Bilbasen Fiat Panda Finder - Environment Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("[ERROR] Run this script from the project root directory")
        sys.exit(1)
    
    # Determine setup type
    dev_mode = "--dev" in sys.argv or "-d" in sys.argv
    print(f"[INFO] Setting up {'development' if dev_mode else 'production'} environment")
    
    # Run setup steps
    steps = [
        ("Virtual Environment", setup_virtual_environment),
        ("Dependencies", lambda: install_dependencies(dev_mode)),
        ("Runtime Directories", setup_runtime_directories),
        ("Git Hooks", setup_git_hooks) if dev_mode else None,
    ]
    
    for step_name, step_func in filter(None, steps):
        try:
            if not step_func():
                print(f"\n[ERROR] Setup failed at step: {step_name}")
                sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] Unexpected error in {step_name}: {e}")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ Setup completed successfully!")
    print("\nNext steps:")
    
    if os.name == "nt":
        print("1. Activate environment: venv\\Scripts\\activate")
    else:
        print("1. Activate environment: source venv/bin/activate")
    
    print("2. Run the application: python launch.py")
    print("3. Visit: http://127.0.0.1:8001")
    
    if dev_mode:
        print("\nDevelopment tools:")
        print("- Run tests: pytest")
        print("- Format code: black src/ tests/")
        print("- Lint code: ruff check src/ tests/")
        print("- Type check: mypy src/")


if __name__ == "__main__":
    main()