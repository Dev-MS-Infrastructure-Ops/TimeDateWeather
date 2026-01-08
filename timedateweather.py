import tkinter as tk
import time
import threading
import urllib.request
import json
import ctypes

# ==========================================
#              CONFIGURATION
# ==========================================
ZIP_CODE = "80701"        # Your Zip Code (e.g., "10001" or "SW1A 2AA")
LOCATION_COUNTRY = "US"   # Optional: Helps accuracy (US, GB, etc.)

# Appearance
FONT_FAMILY = "Segoe UI"  # Windows 11 standard font
TIME_SIZE = 48
DATE_SIZE = 16
WEATHER_SIZE = 16
STATUS_SIZE = 11          # Smaller font for status messages
TEXT_COLOR = "#ffffff"    # Hex color (white)
STATUS_COLOR = "#808080"  # Gray (50% opacity effect)
SHADOW_COLOR = "#000000"  # Text shadow for readability
OPACITY = 1.0             # Window transparency (0.1 to 1.0)

# Time Format
USE_24H_FORMAT = False    # True for 24-hour format, False for 12-hour format (default)
SHOW_SECONDS = False      # True to show seconds, False for minutes only (default)

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
        self.weather_text = f"Loading {ZIP_CODE} Weather"
        self.status_text = "Drag to position - Right-click for menu"  # Status messages line
        self.is_locked = False  # Start unlocked for positioning
        self.is_topmost = False  # Start at desktop level
        self.use_24h = USE_24H_FORMAT  # Time format preference
        self.show_seconds = SHOW_SECONDS  # Show seconds preference
        self.drag_start_x = 0
        self.drag_start_y = 0

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

        # Create context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.lock_var = tk.BooleanVar(value=False)
        self.topmost_var = tk.BooleanVar(value=False)
        self.time_24h_var = tk.BooleanVar(value=USE_24H_FORMAT)
        self.show_seconds_var = tk.BooleanVar(value=SHOW_SECONDS)
        self.context_menu.add_command(label="Refresh Weather", command=self.manual_weather_refresh)
        self.context_menu.add_separator()
        self.context_menu.add_checkbutton(label="Lock Position", variable=self.lock_var, command=self.toggle_lock)
        self.context_menu.add_checkbutton(label="Keep on Top", variable=self.topmost_var, command=self.toggle_topmost)
        self.context_menu.add_checkbutton(label="24-Hour Format", variable=self.time_24h_var, command=self.toggle_time_format)
        self.context_menu.add_checkbutton(label="Show Seconds", variable=self.show_seconds_var, command=self.toggle_show_seconds)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Exit", command=self.root.quit)

        # Drag and lock bindings
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<Button-3>", self.show_context_menu)  # Right-click for menu
        self.root.bind("<Control-l>", self.toggle_lock)  # Ctrl+L to lock/unlock

        # UI Elements (Using Canvas for text shadows/rendering)
        # Make canvas significantly larger (103% coverage) to catch all clicks
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0, width=520, height=140)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Create invisible rectangle covering entire canvas to catch all mouse events
        self.canvas.create_rectangle(0, 0, 520, 140, fill="black", outline="", tags="clickarea")

        # Bind canvas events for larger click area
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.show_context_menu)

        # Also bind to the clickarea rectangle specifically
        self.canvas.tag_bind("clickarea", "<Button-1>", self.start_drag)
        self.canvas.tag_bind("clickarea", "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind("clickarea", "<Button-3>", self.show_context_menu)

        # Draw Text placeholders with proper spacing
        # Status message appears at top (small, subtle)
        self.status_id = self.create_status_text(0, 0, self.status_text)
        # Time display (large, bold)
        self.time_id = self.create_text(0, 18, "", TIME_SIZE, True)
        # Date display (medium spacing after time)
        self.date_id = self.create_text(0, 75, "", DATE_SIZE, False)
        # Weather display (good spacing after date)
        self.weather_id = self.create_text(0, 100, self.weather_text, WEATHER_SIZE, False)

        # Start loops
        self.update_time()
        self.get_weather() # Initial call

        # Clear initial status message after 3 seconds
        self.root.after(3000, self.clear_status_message)

        self.root.mainloop()

    def create_text(self, x, y, text, size, bold):
        # Helper to draw shadow and text on top of clickarea
        font_spec = (FONT_FAMILY, size, "bold" if bold else "normal")
        # Shadow (raise to top layer)
        shadow = self.canvas.create_text(x+2, y+2, text=text, font=font_spec, fill=SHADOW_COLOR, anchor="nw", tag=f"shadow_{y}")
        self.canvas.tag_raise(shadow)
        # Main Text (raise to top layer)
        text_id = self.canvas.create_text(x, y, text=text, font=font_spec, fill=TEXT_COLOR, anchor="nw")
        self.canvas.tag_raise(text_id)
        return text_id

    def create_status_text(self, x, y, text):
        # Helper to draw status text (no shadow, smaller, 50% opacity gray)
        font_spec = (FONT_FAMILY, STATUS_SIZE, "normal")
        # Status text overlays time (raise to top layer)
        text_id = self.canvas.create_text(x, y, text=text, font=font_spec, fill=STATUS_COLOR, anchor="nw")
        self.canvas.tag_raise(text_id)
        return text_id

    def make_click_through(self, enable=True):
        # Uses Windows API to make the black background transparent AND click-through
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20) # GWL_EXSTYLE
        if enable:
            style = style | 0x80000 | 0x20 # WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            style = style & ~0x20  # Remove WS_EX_TRANSPARENT
            style = style | 0x80000  # Keep WS_EX_LAYERED
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)

    def start_drag(self, event):
        if not self.is_locked:
            self.drag_start_x = event.x
            self.drag_start_y = event.y

    def on_drag(self, event):
        if not self.is_locked:
            x = self.root.winfo_x() + (event.x - self.drag_start_x)
            y = self.root.winfo_y() + (event.y - self.drag_start_y)
            self.root.geometry(f"+{x}+{y}")

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def toggle_lock(self, event=None):
        self.is_locked = self.lock_var.get()
        self.make_click_through(self.is_locked)

        # Visual feedback: change opacity slightly when unlocked
        if self.is_locked:
            self.root.attributes("-alpha", OPACITY)
            # Show lock message on status line
            self.status_text = "[LOCKED] Position locked"
            self.update_status_ui()

            # Clear status message after 3 seconds
            self.root.after(3000, self.clear_status_message)
        else:
            self.root.attributes("-alpha", min(1.0, OPACITY + 0.15))
            # Show unlocked message on status line
            self.status_text = "[UNLOCKED] Drag to reposition"
            self.update_status_ui()

            # Clear status message after 3 seconds
            self.root.after(3000, self.clear_status_message)

    def clear_status_message(self):
        # Clear the status line
        self.status_text = ""
        self.update_status_ui()

    def toggle_topmost(self):
        self.is_topmost = self.topmost_var.get()
        self.root.attributes("-topmost", self.is_topmost)

    def toggle_time_format(self):
        self.use_24h = self.time_24h_var.get()
        # Update time display immediately
        self.update_time()

    def toggle_show_seconds(self):
        self.show_seconds = self.show_seconds_var.get()
        # Update time display immediately
        self.update_time()

    def manual_weather_refresh(self):
        # Manually trigger weather refresh
        thread = threading.Thread(target=self.fetch_weather_data)
        thread.daemon = True
        thread.start()

    def update_time(self):
        now = time.localtime()
        # Use 24-hour or 12-hour format based on preference, with or without seconds
        if self.use_24h:
            if self.show_seconds:
                time_str = time.strftime("%H:%M:%S", now)  # 24-hour with seconds (e.g., "14:30:45")
            else:
                time_str = time.strftime("%H:%M", now)  # 24-hour without seconds (e.g., "14:30")
        else:
            if self.show_seconds:
                time_str = time.strftime("%I:%M:%S %p", now).lstrip("0")  # 12-hour with seconds (e.g., "2:30:45 PM")
            else:
                time_str = time.strftime("%I:%M %p", now).lstrip("0")  # 12-hour without seconds (e.g., "2:30 PM")
        date_str = time.strftime("%A, %B %d", now)

        # Update Canvas Items with new Y positions
        self.canvas.itemconfigure(self.time_id, text=time_str)
        self.canvas.itemconfigure(f"shadow_18", text=time_str)

        self.canvas.itemconfigure(self.date_id, text=date_str)
        self.canvas.itemconfigure(f"shadow_75", text=date_str)

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
            # Format: %C = Condition, %t = Temperature, %w = Wind speed
            url = f"https://wttr.in/{ZIP_CODE}?format=%C+%t+%w"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = response.read().decode("utf-8").strip()

            # Update weather text directly - status messages are on separate line now
            self.weather_text = data
        except Exception as e:
            self.weather_text = "Weather Unavailable"

        # Schedule UI update on main thread
        self.root.after(0, self.update_weather_ui)

    def update_weather_ui(self):
        self.canvas.itemconfigure(self.weather_id, text=self.weather_text)
        self.canvas.itemconfigure(f"shadow_100", text=self.weather_text)

    def update_status_ui(self):
        # Update status text only (no shadow for status messages)
        self.canvas.itemconfigure(self.status_id, text=self.status_text)

if __name__ == "__main__":
    DesktopWidget()