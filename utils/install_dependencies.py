#!/usr/bin/env python3

import subprocess
import sys

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ {package} installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {package}: {e}")
        return False

def main():
    """Install all required dependencies"""
    print("Installing DFS Scraper dependencies...")
    print("=" * 50)
    
    packages = [
        "seleniumbase",
        "pyautogui", 
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib"
    ]
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"Installation complete: {success_count}/{len(packages)} packages installed successfully")
    
    if success_count == len(packages):
        print("✓ All dependencies installed! You can now run the scraper.")
    else:
        print("⚠ Some packages failed to install. Please check the errors above.")

if __name__ == "__main__":
    main()
