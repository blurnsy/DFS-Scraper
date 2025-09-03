#!/usr/bin/env python3

import pyautogui
import time
import sys

def display_mouse_coordinates():
    print("Mouse Coordinates Tracker")
    print("Press Ctrl+C to exit")
    print("=" * 40)
    
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\rX: {x:4d} | Y: {y:4d}", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    display_mouse_coordinates()
