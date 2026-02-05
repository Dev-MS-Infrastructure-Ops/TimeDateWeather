"""
Build Script for TimeDateWeather Desktop Widget
Creates standalone Windows executable using PyInstaller.

Usage:
    python build.py          - Build the executable
    python build.py --clean  - Clean build artifacts before building

Requirements:
    pip install pyinstaller
"""

import os
import sys
import shutil
import subprocess

# Application info
APP_NAME = "TimeDateWeather"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "timedateweather.py"

# Build configuration
BUILD_DIR = "build"
DIST_DIR = "dist"
SPEC_FILE = f"{APP_NAME}.spec"
CLEAN_PYINSTALLER = False

# Icon path (create an icon or use None for default)
ICON_PATH = None  # Set to "icon.ico" if you have an icon file


def clean_build():
    """Remove previous build artifacts."""
    print("Cleaning previous build artifacts...")
    dirs_to_remove = [BUILD_DIR, DIST_DIR, "__pycache__"]

    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"  Removed: {dir_name}")
            except Exception as e:
                print(f"  Warning: Could not remove {dir_name} ({e})")

    if os.path.exists(SPEC_FILE):
        os.remove(SPEC_FILE)
        print(f"  Removed: {SPEC_FILE}")

    # Clean pycache in all subdirectories
    for root, dirs, files in os.walk("."):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                pycache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(pycache_path)
                    print(f"  Removed: {pycache_path}")
                except Exception as e:
                    print(f"  Warning: Could not remove {pycache_path} ({e})")


def build_executable():
    """Build the executable using PyInstaller."""
    print(f"\nBuilding {APP_NAME} v{APP_VERSION}...")
    print("=" * 50)

    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("ERROR: PyInstaller is not installed.")
        print("Install it with: pip install pyinstaller")
        return False

    # Construct PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",           # Single executable
        "--windowed",          # No console window
        "--noconfirm",         # Replace output without asking
    ]
    if CLEAN_PYINSTALLER:
        cmd.append("--clean")  # Clean PyInstaller cache

    # Add icon if available
    if ICON_PATH and os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])
        print(f"Using icon: {ICON_PATH}")

    # Add version info if available
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version_info.txt")
    if os.path.exists(version_file):
        cmd.extend(["--version-file", version_file])

    # Add hidden imports for modules that PyInstaller might miss
    hidden_imports = [
        "tkinter",
        "tkinter.ttk",
        "tkinter.colorchooser",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "pystray",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Add data files to include
    data_files = [
        ("themes.py", "."),
        ("notifications.py", "."),
        ("config_manager.py", "."),
        ("settings_window.py", "."),
    ]

    # Add the main script
    cmd.append(MAIN_SCRIPT)

    print(f"\nCommand: {' '.join(cmd)}\n")

    # Run PyInstaller
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    if result.returncode == 0:
        exe_path = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print("\n" + "=" * 50)
            print(f"SUCCESS! Executable created:")
            print(f"  {os.path.abspath(exe_path)}")
            print(f"  Size: {size_mb:.2f} MB")
            print("=" * 50)
            return True
        else:
            print("ERROR: Executable was not created.")
            return False
    else:
        print(f"ERROR: PyInstaller failed with return code {result.returncode}")
        return False


def create_version_info():
    """Create version info file for Windows."""
    version_parts = APP_VERSION.split(".")
    while len(version_parts) < 4:
        version_parts.append("0")

    version_tuple = tuple(int(v) for v in version_parts[:4])

    version_info = f'''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'MS-I'),
            StringStruct(u'FileDescription', u'{APP_NAME} Desktop Widget'),
            StringStruct(u'FileVersion', u'{APP_VERSION}'),
            StringStruct(u'InternalName', u'{APP_NAME}'),
            StringStruct(u'LegalCopyright', u'Copyright (c) 2025'),
            StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
            StringStruct(u'ProductName', u'{APP_NAME}'),
            StringStruct(u'ProductVersion', u'{APP_VERSION}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    with open("version_info.txt", "w") as f:
        f.write(version_info)
    print("Created version_info.txt")


def main():
    """Main build entry point."""
    print(f"\n{'='*50}")
    print(f"  {APP_NAME} Build Script")
    print(f"  Version: {APP_VERSION}")
    print(f"{'='*50}\n")

    # Check for clean flag
    if "--clean" in sys.argv or "-c" in sys.argv:
        clean_build()

    # Always clean first for a fresh build
    clean_build()

    # Create version info
    create_version_info()

    # Build the executable
    success = build_executable()

    if success:
        print("\nBuild completed successfully!")
        print("\nNext steps:")
        print("1. Test the executable in the 'dist' folder")
        print("2. Run the Inno Setup script to create an installer")
    else:
        print("\nBuild failed. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
