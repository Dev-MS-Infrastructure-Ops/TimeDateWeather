import tkinter as tk
import time
import threading
import urllib.request
import json
import ctypes

# ==========================================
#              CONFIGURATION
# ==========================================
ZIP_CODE = "90210"        # Your Zip Code (e.g., "10001" or "SW1A 2AA")
LOCATION_COUNTRY = "US"   # Optional: Helps accuracy (US, GB, etc.)

# Appearance
FONT_FAMILY = "Segoe UI"  # Windows 11 standard font
TIME_SIZE = 48
DATE_SIZE = 16
WEATHER_SIZE = 16
TEXT_COLOR = "#ffffff"    # Hex color (white)
SHADOW_COLOR = "#000000"  # Text shadow for readability
OPACITY = 1.0             # Window transparency (0.1 to 1.0)

# Position (Coordinates on screen)
POS_X = 50
POS_Y = 50

# Update Intervals (in milliseconds)
TIME_UPDATE = 1000        # 1 second
WEATHER_UPDATE = 1800000  # 30 minutes (saves resources)

# ==========================================
#             WIDGET LOGIC
# ==========================================

class DesktopWidget:
    def __init__(self):
        self.root = tk.Tk()
        self.weather_text = "Loading..."
        
        # Window Setup
        self.root.overrideredirect(True)  # Remove borders
        self.root.geometry(f"+{POS_X}+{POS_Y}")
        self.root.attributes("-topmost", False) # Keep on desktop level
        self.root.wm_attributes("-transparentcolor", "black") # Magic color for transparency
        self.root.attributes("-alpha", OPACITY)
        
        # Enable High DPI (Crisp text on Win11)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # Make Click-Through (Input Transparent)
        self.make_click_through()

        # UI Elements (Using Canvas for text shadows/rendering)
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw Text placeholders
        self.time_id = self.create_text(0, 0, "", TIME_SIZE, True)
        self.date_id = self.create_text(0, 60, "", DATE_SIZE, False)
        self.weather_id = self.create_text(0, 90, self.weather_text, WEATHER_SIZE, False)

        # Start loops
        self.update_time()
        self.get_weather() # Initial call
        
        self.root.mainloop()

    def create_text(self, x, y, text, size, bold):
        # Helper to draw shadow and text
        font_spec = (FONT_FAMILY, size, "bold" if bold else "normal")
        # Shadow
        self.canvas.create_text(x+2, y+2, text=text, font=font_spec, fill=SHADOW_COLOR, anchor="nw", tag=f"shadow_{y}")
        # Main Text
        return self.canvas.create_text(x, y, text=text, font=font_spec, fill=TEXT_COLOR, anchor="nw")

    def make_click_through(self):
        # Uses Windows API to make the black background transparent AND click-through
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20) # GWL_EXSTYLE
        style = style | 0x80000 | 0x20 # WS_EX_LAYERED | WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)

    def update_time(self):
        now = time.localtime()
        time_str = time.strftime("%I:%M %p", now).lstrip("0") # 12-hour format
        date_str = time.strftime("%A, %B %d", now)
        
        # Update Canvas Items
        self.canvas.itemconfigure(self.time_id, text=time_str)
        self.canvas.itemconfigure(f"shadow_0", text=time_str)
        
        self.canvas.itemconfigure(self.date_id, text=date_str)
        self.canvas.itemconfigure(f"shadow_60", text=date_str)
        
        self.root.after(TIME_UPDATE, self.update_time)

    def get_weather(self):
        # Run in separate thread to prevent GUI freezing
        thread = threading.Thread(target=self.fetch_weather_data)
        thread.daemon = True
        thread.start()
        # Schedule next update
        self.root.after(WEATHER_UPDATE, self.get_weather)

    def fetch_weather_data(self):
        try:
            # Using wttr.in (free, no API key required)
            # format=j1 gives JSON. We can also use format=3 for simple text.
            # Using simple text format for extreme efficiency and parsing speed.
            url = f"https://wttr.in/{ZIP_CODE}?format=%C+%t"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = response.read().decode("utf-8").strip()
                
            self.weather_text = data
        except Exception as e:
            self.weather_text = "Weather Unavailable"
        
        # Schedule UI update on main thread
        self.root.after(0, self.update_weather_ui)

    def update_weather_ui(self):
        self.canvas.itemconfigure(self.weather_id, text=self.weather_text)
        self.canvas.itemconfigure(f"shadow_90", text=self.weather_text)

if __name__ == "__main__":
    DesktopWidget()