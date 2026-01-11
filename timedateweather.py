import tkinter as tk
from tkinter import messagebox
import time
import threading
import urllib.request
import json
import ctypes
import os
import sys
import winsound
from config_manager import ConfigManager

# Application version
APP_VERSION = "1.0.0"

# Weather condition to emoji mapping
WEATHER_EMOJIS = {
    "sunny": "\u2600\ufe0f",      # Sun
    "clear": "\u2600\ufe0f",      # Sun (for clear day)
    "partly cloudy": "\u26c5",    # Sun behind cloud
    "cloudy": "\u2601\ufe0f",     # Cloud
    "overcast": "\u2601\ufe0f",   # Cloud
    "mist": "\ud83c\udf2b\ufe0f", # Fog
    "fog": "\ud83c\udf2b\ufe0f",  # Fog
    "light rain": "\ud83c\udf27\ufe0f",   # Cloud with rain
    "rain": "\ud83c\udf27\ufe0f",         # Cloud with rain
    "heavy rain": "\ud83c\udf27\ufe0f",   # Cloud with rain
    "drizzle": "\ud83c\udf26\ufe0f",      # Sun behind rain cloud
    "thunderstorm": "\u26c8\ufe0f",       # Thunder cloud
    "thunder": "\u26c8\ufe0f",            # Thunder cloud
    "snow": "\u2744\ufe0f",               # Snowflake
    "light snow": "\ud83c\udf28\ufe0f",   # Cloud with snow
    "heavy snow": "\u2744\ufe0f",         # Snowflake
    "sleet": "\ud83c\udf28\ufe0f",        # Cloud with snow
    "hail": "\ud83c\udf28\ufe0f",         # Cloud with snow
    "windy": "\ud83d\udca8",              # Dash (wind)
    "hot": "\ud83c\udf21\ufe0f",          # Thermometer
    "cold": "\u2744\ufe0f",               # Snowflake
}

# ==========================================
#              CONFIGURATION
# ==========================================
# Configuration now loaded from settings.json via ConfigManager
# See config_manager.py for default values

# ==========================================
#             WIDGET LOGIC
# ==========================================

class DesktopWidget:
    def __init__(self, instance_id="instance_1", is_new=False):
        self.root = tk.Tk()
        self.instance_id = instance_id

        # Load configuration for this instance
        self.config = ConfigManager(instance_id=instance_id)

        # Track if this is a newly created instance
        self.is_new_instance = is_new

        # Track position changes for smart exit dialog
        self.position_changed_since_save = False
        self.last_saved_position = (
            self.config.get('position', 'x'),
            self.config.get('position', 'y')
        )

        self.weather_text = f"Loading {self.config.get('location', 'zip_code')} Weather"
        self.status_text = "Drag to position - Right-click for menu"  # Status messages line
        self.is_locked = False  # Start unlocked for positioning
        self.is_topmost = False  # Start at desktop level
        self.use_24h = self.config.get('display', 'use_24h_format')  # Time format preference
        self.show_seconds = self.config.get('display', 'show_seconds')  # Show seconds preference
        self.settings_border_visible = False  # Track if settings border is shown
        self.last_hour_chimed = -1  # Track last hour we played chime for
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Window Setup
        self.root.overrideredirect(True)  # Remove borders
        self.root.geometry(f"+{self.last_saved_position[0]}+{self.last_saved_position[1]}")
        self.root.attributes("-topmost", False) # Keep on desktop level
        self.root.wm_attributes("-transparentcolor", "black") # Magic color for transparency
        self.root.attributes("-alpha", self.config.get('appearance', 'opacity'))

        # Set window title for instance identification (useful for debugging)
        self.root.title(f"TimeDateWeather - {instance_id}")

        # Enable High DPI (Crisp text on Win11)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # Create context menu with keyboard shortcut hints
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.lock_var = tk.BooleanVar(value=False)
        self.topmost_var = tk.BooleanVar(value=False)
        self.time_24h_var = tk.BooleanVar(value=self.config.get('display', 'use_24h_format'))
        self.show_seconds_var = tk.BooleanVar(value=self.config.get('display', 'show_seconds'))
        self.context_menu.add_command(label="Refresh Weather (Ctrl+R)", command=self.manual_weather_refresh)
        self.context_menu.add_separator()
        self.context_menu.add_checkbutton(label="Lock Position (Ctrl+L)", variable=self.lock_var, command=self.toggle_lock)
        self.context_menu.add_checkbutton(label="Keep on Top", variable=self.topmost_var, command=self.toggle_topmost)
        self.context_menu.add_checkbutton(label="24-Hour Format", variable=self.time_24h_var, command=self.toggle_time_format)
        self.context_menu.add_checkbutton(label="Show Seconds", variable=self.show_seconds_var, command=self.toggle_show_seconds)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Settings... (Ctrl+S)", command=self.open_settings)
        self.context_menu.add_command(label="About...", command=self.show_about)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Launch New Instance", command=self.launch_new_instance)
        self.context_menu.add_command(label="Exit This Instance", command=self.on_exit)
        self.context_menu.add_command(label="Exit All Instances", command=self.exit_all_instances)

        # Highlight border reference
        self.highlight_border = None

        # Drag and lock bindings
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.end_drag)  # Save position on drag end
        self.root.bind("<Button-3>", self.show_context_menu)  # Right-click for menu

        # Keyboard shortcuts
        self.root.bind("<Control-l>", self.toggle_lock)  # Ctrl+L to lock/unlock
        self.root.bind("<Control-r>", lambda e: self.manual_weather_refresh())  # Ctrl+R to refresh weather
        self.root.bind("<Control-s>", lambda e: self.open_settings())  # Ctrl+S for settings

        # Exit handler for smart position save dialog
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        # UI Elements (Using Canvas for text shadows/rendering)
        # Calculate canvas size based on scale and font size
        self.scale = self.config.get('appearance', 'scale')

        # Calculate font-based scale factor
        time_size = self.config.get('fonts', 'time_size')
        date_size = self.config.get('fonts', 'date_size')
        weather_size = self.config.get('fonts', 'weather_size')
        max_font_size = max(time_size, date_size, weather_size)
        font_scale_factor = max(1.0, max_font_size / 48.0)
        total_scale = self.scale * font_scale_factor

        self.canvas_width = int(520 * total_scale)
        self.canvas_height = int(140 * total_scale)
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0, width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Create invisible rectangle covering entire canvas to catch all mouse events
        self.canvas.create_rectangle(0, 0, self.canvas_width, self.canvas_height, fill="black", outline="", tags="clickarea")

        # Bind ALL canvas events for complete coverage
        # Use bind_all on canvas to catch events even when they hit text
        self.canvas.bind("<Button-1>", self.start_drag, add="+")
        self.canvas.bind("<B1-Motion>", self.on_drag, add="+")
        self.canvas.bind("<ButtonRelease-1>", self.end_drag, add="+")
        self.canvas.bind("<Button-3>", self.show_context_menu, add="+")

        # Also bind to the clickarea rectangle
        self.canvas.tag_bind("clickarea", "<Button-1>", self.start_drag, add="+")
        self.canvas.tag_bind("clickarea", "<B1-Motion>", self.on_drag, add="+")
        self.canvas.tag_bind("clickarea", "<ButtonRelease-1>", self.end_drag, add="+")
        self.canvas.tag_bind("clickarea", "<Button-3>", self.show_context_menu, add="+")

        # Bind to ALL canvas items (catch everything)
        self.canvas.tag_bind("all", "<Button-3>", self.show_context_menu, add="+")
        self.canvas.tag_bind("text", "<Button-1>", self.start_drag, add="+")
        self.canvas.tag_bind("text", "<B1-Motion>", self.on_drag, add="+")
        self.canvas.tag_bind("text", "<ButtonRelease-1>", self.end_drag, add="+")
        self.canvas.tag_bind("shadow", "<Button-3>", self.show_context_menu, add="+")
        self.canvas.tag_bind("shadow", "<Button-1>", self.start_drag, add="+")
        self.canvas.tag_bind("shadow", "<B1-Motion>", self.on_drag, add="+")
        self.canvas.tag_bind("shadow", "<ButtonRelease-1>", self.end_drag, add="+")

        # Draw Text placeholders with proper spacing (scaled)
        # Status message appears at top (small, subtle)
        self.status_id = self.create_status_text(
            int(self.config.get('spacing', 'status_x') * self.scale),
            int(self.config.get('spacing', 'status_y') * self.scale),
            self.status_text
        )
        # Time display (large, bold)
        time_color = self.config.get('colors', 'time_color') if not self.config.get('colors', 'lock_colors') else None
        self.time_id = self.create_text(
            int(self.config.get('spacing', 'time_x') * self.scale),
            int(self.config.get('spacing', 'time_y') * self.scale),
            "", self.config.get('fonts', 'time_size'), True, time_color
        )
        # Date display (medium spacing after time)
        date_color = self.config.get('colors', 'date_color') if not self.config.get('colors', 'lock_colors') else None
        self.date_id = self.create_text(
            int(self.config.get('spacing', 'date_x') * self.scale),
            int(self.config.get('spacing', 'date_y') * self.scale),
            "", self.config.get('fonts', 'date_size'), False, date_color
        )
        # Weather display (good spacing after date)
        weather_color = self.config.get('colors', 'weather_color') if not self.config.get('colors', 'lock_colors') else None
        self.weather_id = self.create_text(
            int(self.config.get('spacing', 'weather_x') * self.scale),
            int(self.config.get('spacing', 'weather_y') * self.scale),
            self.weather_text, self.config.get('fonts', 'weather_size'), False, weather_color
        )

        # Start loops
        self.update_time()
        self.get_weather() # Initial call

        # Ensure widget is visible on screen (multi-monitor awareness)
        self.root.after(100, self.ensure_on_screen)

        # Clear initial status message after 3 seconds
        self.root.after(3000, self.clear_status_message)

        # Show highlight for new instances
        if self.is_new_instance:
            self.show_new_instance_highlight()

        self.root.mainloop()

    def create_text(self, x, y, text, size, bold, color=None):
        # Helper to draw shadow and text on top of clickarea (scaled)
        scaled_size = int(size * self.scale)
        shadow_offset_x = int(self.config.get('appearance', 'shadow_offset_x') * self.scale)
        shadow_offset_y = int(self.config.get('appearance', 'shadow_offset_y') * self.scale)
        font_spec = (self.config.get('fonts', 'family'), scaled_size, "bold" if bold else "normal")

        # Use provided color or fallback to text color
        if color is None:
            color = self.config.get('colors', 'text')

        # Shadow (raise to top layer with shadow tag)
        shadow = self.canvas.create_text(x+shadow_offset_x, y+shadow_offset_y, text=text, font=font_spec, fill=self.config.get('colors', 'shadow'), anchor="nw", tags=("shadow", f"shadow_{y}"))
        self.canvas.tag_raise(shadow)
        # Main Text (raise to top layer with text tag)
        text_id = self.canvas.create_text(x, y, text=text, font=font_spec, fill=color, anchor="nw", tags="text")
        self.canvas.tag_raise(text_id)
        return text_id

    def create_status_text(self, x, y, text):
        # Helper to draw status text (no shadow, smaller, 50% opacity gray) (scaled)
        scaled_size = int(self.config.get('fonts', 'status_size') * self.scale)
        font_spec = (self.config.get('fonts', 'family'), scaled_size, "normal")
        # Status text overlays time (raise to top layer with text tag)
        text_id = self.canvas.create_text(x, y, text=text, font=font_spec, fill=self.config.get('colors', 'status'), anchor="nw", tags="text")
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
        # Remove highlight on first interaction
        if self.is_new_instance:
            self.remove_new_instance_highlight()

        if not self.is_locked:
            self.drag_start_x = event.x
            self.drag_start_y = event.y

    def on_drag(self, event):
        if not self.is_locked:
            x = self.root.winfo_x() + (event.x - self.drag_start_x)
            y = self.root.winfo_y() + (event.y - self.drag_start_y)
            # Apply snap-to-edge
            x, y = self.snap_to_edge(x, y)
            self.root.geometry(f"+{x}+{y}")
            # Mark that position has changed
            self.position_changed_since_save = True

    def end_drag(self, event):
        """Save position when drag ends (Option C: save on mouse release)."""
        if not self.is_locked and self.position_changed_since_save:
            self.save_current_position()

    def show_context_menu(self, event):
        # Remove highlight on right-click
        if self.is_new_instance:
            self.remove_new_instance_highlight()

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def toggle_lock(self, event=None):
        self.is_locked = self.lock_var.get()
        self.make_click_through(self.is_locked)

        # Visual feedback: change opacity slightly when unlocked
        opacity = self.config.get('appearance', 'opacity')
        if self.is_locked:
            self.root.attributes("-alpha", opacity)
            # Save position when locked
            self.save_current_position()
            # Show lock message on status line
            self.status_text = "[LOCKED] Position locked & saved"
            self.update_status_ui()

            # Clear status message after 3 seconds
            self.root.after(3000, self.clear_status_message)
        else:
            self.root.attributes("-alpha", min(1.0, opacity + 0.15))
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

        # Use configurable date format
        date_format = self.config.get('display', 'date_format') or "%A, %B %d"
        date_str = time.strftime(date_format, now)

        # Check for top of hour chime
        if self.config.get('display', 'hourly_chime'):
            current_hour = now.tm_hour
            current_minute = now.tm_min
            # Play chime at top of hour (minute 00) and only once per hour
            if current_minute == 0 and self.last_hour_chimed != current_hour:
                self.play_hourly_chime()
                self.last_hour_chimed = current_hour

        # Update Canvas Items with new Y positions
        self.canvas.itemconfigure(self.time_id, text=time_str)
        self.canvas.itemconfigure(f"shadow_18", text=time_str)

        self.canvas.itemconfigure(self.date_id, text=date_str)
        self.canvas.itemconfigure(f"shadow_75", text=date_str)

        self.root.after(self.config.get('updates', 'time_interval'), self.update_time)

    def get_weather(self):
        # Run in separate thread to prevent GUI freezing
        thread = threading.Thread(target=self.fetch_weather_data)
        thread.daemon = True
        thread.start()
        # Schedule next update
        self.root.after(self.config.get('updates', 'weather_interval'), self.get_weather)

    def fetch_weather_data(self):
        try:
            # Using wttr.in (free, no API key required)
            zip_code = self.config.get('location', 'zip_code')

            # Check if forecast is enabled
            if self.config.get('weather', 'show_forecast'):
                # Fetch forecast data (today + tomorrow)
                forecast_days = self.config.get('weather', 'forecast_days') or 1
                url = f"https://wttr.in/{zip_code}?format=%C+%t+%w"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    today_data = response.read().decode("utf-8").strip()

                # Get tomorrow's forecast
                url_tomorrow = f"https://wttr.in/{zip_code}?format=%C+%t&1"
                req_tomorrow = urllib.request.Request(url_tomorrow, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req_tomorrow) as response:
                    tomorrow_data = response.read().decode("utf-8").strip()

                data = f"{today_data} | Tomorrow: {tomorrow_data}"
            else:
                # Get format string based on user preference
                display_format = self.config.get('weather', 'display_format')
                format_strings = self.config.get('weather', 'format_strings')
                format_string = format_strings.get(display_format, "%C+%t+%w")

                url = f"https://wttr.in/{zip_code}?format={format_string}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = response.read().decode("utf-8").strip()

            # Add weather emoji if enabled
            if self.config.get('weather', 'show_emoji'):
                data = self._add_weather_emoji(data)

            self.weather_text = data
        except Exception as e:
            self.weather_text = "Weather Unavailable"

        # Schedule UI update on main thread
        self.root.after(0, self.update_weather_ui)

    def _add_weather_emoji(self, weather_text):
        """Add emoji based on weather condition in the text."""
        weather_lower = weather_text.lower()
        for condition, emoji in WEATHER_EMOJIS.items():
            if condition in weather_lower:
                return f"{emoji} {weather_text}"
        return weather_text

    def update_weather_ui(self):
        self.canvas.itemconfigure(self.weather_id, text=self.weather_text)
        self.canvas.itemconfigure(f"shadow_100", text=self.weather_text)

    def update_status_ui(self):
        # Update status text only (no shadow for status messages)
        self.canvas.itemconfigure(self.status_id, text=self.status_text)

    def play_hourly_chime(self):
        """Play a sound notification at the top of the hour."""
        try:
            # Play system beep in a separate thread to avoid blocking
            def play_sound():
                try:
                    # Play Windows system sound (simple beep)
                    # Frequency: 1000 Hz, Duration: 200 ms
                    winsound.Beep(1000, 200)
                except Exception:
                    pass  # Silent failure if sound can't play

            thread = threading.Thread(target=play_sound)
            thread.daemon = True
            thread.start()
        except Exception:
            pass  # Silent failure

    def open_settings(self):
        """Open the settings window."""
        try:
            from settings_window import SettingsWindow
            SettingsWindow(self)
        except Exception as e:
            # Silent failure - no error dialogs
            pass

    def show_about(self):
        """Show the About dialog with version and shortcut information."""
        about_text = f"""TimeDateWeather Desktop Widget
Version {APP_VERSION}

A lightweight, customizable desktop widget displaying:
  \u2022 Current time (12/24 hour format)
  \u2022 Date (multiple format options)
  \u2022 Local weather from wttr.in

Keyboard Shortcuts:
  Ctrl+L - Lock/Unlock position
  Ctrl+R - Refresh weather
  Ctrl+S - Open settings

Features:
  \u2022 Multiple widget instances
  \u2022 Theme presets
  \u2022 Weather emojis
  \u2022 Hourly chime
  \u2022 Auto-start with Windows

Right-click the widget for quick options."""
        messagebox.showinfo("About TimeDateWeather", about_text)

    def ensure_on_screen(self):
        """Ensure widget is visible on at least one monitor."""
        try:
            # Get widget bounds
            widget_x = self.root.winfo_x()
            widget_y = self.root.winfo_y()

            # Get virtual screen bounds (all monitors combined) using Windows API
            user32 = ctypes.windll.user32
            # SM_XVIRTUALSCREEN = 76, SM_YVIRTUALSCREEN = 77
            virtual_x = user32.GetSystemMetrics(76)
            virtual_y = user32.GetSystemMetrics(77)
            # SM_CXVIRTUALSCREEN = 78, SM_CYVIRTUALSCREEN = 79
            virtual_width = user32.GetSystemMetrics(78)
            virtual_height = user32.GetSystemMetrics(79)

            # Ensure at least 100px of widget is visible
            min_visible = 100
            new_x = widget_x
            new_y = widget_y

            # Check horizontal bounds
            if widget_x < virtual_x - self.canvas_width + min_visible:
                new_x = virtual_x
            elif widget_x > virtual_x + virtual_width - min_visible:
                new_x = virtual_x + virtual_width - self.canvas_width

            # Check vertical bounds
            if widget_y < virtual_y - self.canvas_height + min_visible:
                new_y = virtual_y
            elif widget_y > virtual_y + virtual_height - min_visible:
                new_y = virtual_y + virtual_height - self.canvas_height

            # Reposition if needed
            if new_x != widget_x or new_y != widget_y:
                self.root.geometry(f"+{new_x}+{new_y}")
                self.show_status_message("Widget repositioned to visible area")
                return True
            return False
        except Exception:
            # Fallback to primary screen if Windows API fails
            try:
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                widget_x = self.root.winfo_x()
                widget_y = self.root.winfo_y()

                new_x = max(0, min(widget_x, screen_width - 100))
                new_y = max(0, min(widget_y, screen_height - 50))

                if new_x != widget_x or new_y != widget_y:
                    self.root.geometry(f"+{new_x}+{new_y}")
                    return True
            except Exception:
                pass
            return False

    def snap_to_edge(self, x, y):
        """Snap widget to screen edges if within snap distance."""
        if not self.config.get('display', 'snap_to_edges'):
            return x, y

        snap_distance = self.config.get('display', 'snap_distance') or 15

        try:
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            widget_width = self.canvas_width
            widget_height = self.canvas_height

            # Snap to left edge
            if abs(x) < snap_distance:
                x = 0
            # Snap to right edge
            elif abs(x + widget_width - screen_width) < snap_distance:
                x = screen_width - widget_width

            # Snap to top edge
            if abs(y) < snap_distance:
                y = 0
            # Snap to bottom edge
            elif abs(y + widget_height - screen_height) < snap_distance:
                y = screen_height - widget_height

        except Exception:
            pass

        return x, y

    def show_status_message(self, message, duration=3000):
        """Show a temporary status message."""
        self.status_text = message
        self.update_status_ui()
        self.root.after(duration, self.clear_status_message)

    def show_settings_border(self, show=True):
        """Show or hide border around canvas when settings menu is open."""
        try:
            self.settings_border_visible = show
            if show:
                # Add a visible border using configurable color
                border_color = self.config.get('ui', 'settings_border_color') or "#ffff00"
                self.canvas.config(highlightthickness=2, highlightbackground=border_color)
            else:
                # Remove border
                self.canvas.config(highlightthickness=0)
        except Exception:
            # Silent failure
            pass

    def show_new_instance_highlight(self):
        """Show animated highlight border for new instances."""
        try:
            # Pulsing border to indicate new instance using configurable color
            highlight_color = self.config.get('ui', 'new_instance_color') or "#00ff00"
            self.canvas.config(highlightthickness=3, highlightbackground=highlight_color)
            self.highlight_pulse_state = 0
            self.pulse_highlight()
        except Exception:
            pass

    def pulse_highlight(self):
        """Pulse the highlight border."""
        if not self.is_new_instance:
            return

        try:
            # Alternate between bright and dim colors using config
            bright_color = self.config.get('ui', 'new_instance_color') or "#00ff00"
            dim_color = self.config.get('ui', 'new_instance_color_dim') or "#00aa00"
            colors = [bright_color, dim_color, bright_color, dim_color]
            self.highlight_pulse_state = (self.highlight_pulse_state + 1) % len(colors)
            self.canvas.config(highlightbackground=colors[self.highlight_pulse_state])

            # Continue pulsing
            self.root.after(500, self.pulse_highlight)
        except Exception:
            pass

    def remove_new_instance_highlight(self):
        """Remove the new instance highlight."""
        try:
            self.is_new_instance = False
            self.canvas.config(highlightthickness=0)
        except Exception:
            pass

    def apply_settings(self):
        """Apply current config settings to widget (called by settings window for live preview)."""
        try:
            # Update time display preferences
            self.use_24h = self.config.get('display', 'use_24h_format')
            self.show_seconds = self.config.get('display', 'show_seconds')
            self.time_24h_var.set(self.use_24h)
            self.show_seconds_var.set(self.show_seconds)

            # Update scale and recalculate canvas size dynamically
            self.scale = self.config.get('appearance', 'scale')

            # Calculate additional scale factor based on largest font size
            time_size = self.config.get('fonts', 'time_size')
            date_size = self.config.get('fonts', 'date_size')
            weather_size = self.config.get('fonts', 'weather_size')
            max_font_size = max(time_size, date_size, weather_size)

            # Base font size is 48 (default time size), scale canvas if fonts are larger
            font_scale_factor = max(1.0, max_font_size / 48.0)

            # Apply both manual scale and font-based scale
            total_scale = self.scale * font_scale_factor

            # Calculate canvas dimensions with dynamic scaling
            self.canvas_width = int(520 * total_scale)
            self.canvas_height = int(140 * total_scale)

            # Preserve border state when reconfiguring canvas
            if self.settings_border_visible:
                self.canvas.config(width=self.canvas_width, height=self.canvas_height,
                                 highlightthickness=2, highlightbackground="#ffff00")
            else:
                self.canvas.config(width=self.canvas_width, height=self.canvas_height)

            # Update opacity
            self.root.attributes("-alpha", self.config.get('appearance', 'opacity'))

            # Recreate text elements with new fonts/colors
            # This is the most efficient way to update all visual properties
            self.canvas.delete("all")

            # Recreate clickarea with new size
            self.canvas.create_rectangle(0, 0, self.canvas_width, self.canvas_height, fill="black", outline="", tags="clickarea")

            # Bind events to new clickarea
            self.canvas.tag_bind("clickarea", "<Button-1>", self.start_drag)
            self.canvas.tag_bind("clickarea", "<B1-Motion>", self.on_drag)
            self.canvas.tag_bind("clickarea", "<ButtonRelease-1>", self.end_drag)
            self.canvas.tag_bind("clickarea", "<Button-3>", self.show_context_menu)

            # Recreate text elements with scaled positions
            self.status_id = self.create_status_text(
                int(self.config.get('spacing', 'status_x') * self.scale),
                int(self.config.get('spacing', 'status_y') * self.scale),
                self.status_text
            )
            # Use individual colors if unlocked
            time_color = self.config.get('colors', 'time_color') if not self.config.get('colors', 'lock_colors') else None
            self.time_id = self.create_text(
                int(self.config.get('spacing', 'time_x') * self.scale),
                int(self.config.get('spacing', 'time_y') * self.scale),
                "", self.config.get('fonts', 'time_size'), True, time_color
            )
            date_color = self.config.get('colors', 'date_color') if not self.config.get('colors', 'lock_colors') else None
            self.date_id = self.create_text(
                int(self.config.get('spacing', 'date_x') * self.scale),
                int(self.config.get('spacing', 'date_y') * self.scale),
                "", self.config.get('fonts', 'date_size'), False, date_color
            )
            weather_color = self.config.get('colors', 'weather_color') if not self.config.get('colors', 'lock_colors') else None
            self.weather_id = self.create_text(
                int(self.config.get('spacing', 'weather_x') * self.scale),
                int(self.config.get('spacing', 'weather_y') * self.scale),
                self.weather_text, self.config.get('fonts', 'weather_size'), False, weather_color
            )

            # Force immediate time update to show new settings
            self.update_time()
            self.update_weather_ui()
        except Exception:
            # Silent failure
            pass

    def save_current_position(self):
        """Save current window position to config (silent failure on error)."""
        try:
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            self.config.set('position', 'x', x)
            self.config.set('position', 'y', y)
            self.config.save()
            # Update tracking variables
            self.last_saved_position = (x, y)
            self.position_changed_since_save = False
        except Exception:
            # Silent failure - no dialogs on error (handles force close gracefully)
            pass

    def set_launch_at_boot(self, enable):
        """Enable or disable launch at Windows startup."""
        try:
            # Get path to Windows startup folder
            startup_folder = os.path.join(
                os.environ['APPDATA'],
                r'Microsoft\Windows\Start Menu\Programs\Startup'
            )

            # Name of the shortcut file
            shortcut_name = 'TimeDateWeather.lnk'
            shortcut_path = os.path.join(startup_folder, shortcut_name)

            if enable:
                # Create shortcut using Windows Script Host
                import winshell
                from win32com.client import Dispatch

                # Get path to this script or executable
                if getattr(sys, 'frozen', False):
                    # Running as compiled executable
                    target_path = sys.executable
                else:
                    # Running as script
                    target_path = sys.executable  # python.exe
                    arguments = f'"{os.path.abspath(__file__)}"'

                # Create shortcut
                shell = Dispatch('WScript.Shell')
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.TargetPath = target_path
                if not getattr(sys, 'frozen', False):
                    shortcut.Arguments = arguments
                shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(__file__))
                shortcut.IconLocation = target_path
                shortcut.save()

            else:
                # Remove shortcut if it exists
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)

        except ImportError:
            # winshell or pywin32 not available, try alternative method
            try:
                if enable:
                    # Create a batch file as fallback
                    batch_path = os.path.join(startup_folder, 'TimeDateWeather.bat')
                    script_path = os.path.abspath(__file__)
                    with open(batch_path, 'w') as f:
                        if getattr(sys, 'frozen', False):
                            f.write(f'@echo off\nstart "" "{sys.executable}"\n')
                        else:
                            f.write(f'@echo off\nstart "" "{sys.executable}" "{script_path}"\n')
                else:
                    # Remove batch file
                    batch_path = os.path.join(startup_folder, 'TimeDateWeather.bat')
                    if os.path.exists(batch_path):
                        os.remove(batch_path)
            except Exception:
                pass  # Silent failure
        except Exception:
            pass  # Silent failure

    def launch_new_instance(self):
        """Launch a new widget instance."""
        try:
            # Generate new instance ID
            all_instances = self.config.get_all_instances()
            instance_num = 1
            while f"instance_{instance_num}" in all_instances:
                instance_num += 1
            new_instance_id = f"instance_{instance_num}"

            # Add new instance to config
            self.config.add_instance(new_instance_id)

            # Launch new process with the new instance ID and new flag
            import subprocess
            script_path = os.path.abspath(__file__)
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                subprocess.Popen([sys.executable, new_instance_id, "--new"])
            else:
                # Running as script
                subprocess.Popen([sys.executable, script_path, new_instance_id, "--new"])
        except Exception as e:
            pass  # Silent failure

    def exit_all_instances(self):
        """Exit all running instances."""
        try:
            response = messagebox.askyesno(
                "Exit All Instances",
                "Are you sure you want to close all widget instances?",
                icon='warning'
            )

            if response:
                # Use taskkill to close all Python processes running this script
                script_name = os.path.basename(__file__)
                if getattr(sys, 'frozen', False):
                    # For executable
                    exe_name = os.path.basename(sys.executable)
                    os.system(f'taskkill /F /IM "{exe_name}" /T')
                else:
                    self.on_exit()
        except Exception:
            pass

    def on_exit(self):
        """Handle application exit with smart position save dialog."""
        try:
            # Check if position has changed since last save
            current_x = self.root.winfo_x()
            current_y = self.root.winfo_y()
            position_changed = (current_x != self.last_saved_position[0] or
                              current_y != self.last_saved_position[1])

            if position_changed:
                # Show confirmation dialog
                response = messagebox.askyesno(
                    "Save Position",
                    "Do you want to save the current widget position?",
                    icon='question'
                )

                if response:  # YES - save current position
                    self.config.set('position', 'x', current_x)
                    self.config.set('position', 'y', current_y)
                    self.config.save()
                else:  # NO - position will revert to last saved on next launch
                    pass  # Don't save, config already has last saved position

            # Exit application
            self.root.quit()
            self.root.destroy()
        except Exception:
            # Silent failure - force quit if any error
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass

def launch_all_active_instances():
    """Launch all active instances on startup."""
    try:
        # Load config to get active instances
        config = ConfigManager()
        active_instances = config.get_active_instances()

        # Launch each instance in a separate process
        import subprocess
        script_path = os.path.abspath(__file__)

        for instance_id in active_instances:
            if instance_id != "instance_1":  # Don't relaunch the first one
                try:
                    if getattr(sys, 'frozen', False):
                        subprocess.Popen([sys.executable, instance_id])
                    else:
                        subprocess.Popen([sys.executable, script_path, instance_id])
                except Exception:
                    pass
    except Exception:
        pass

if __name__ == "__main__":
    # Check for instance ID argument
    instance_id = "instance_1"
    is_new = False

    if len(sys.argv) > 1:
        instance_id = sys.argv[1]
        # Check for --new flag
        if len(sys.argv) > 2 and sys.argv[2] == "--new":
            is_new = True

    # If this is instance_1, launch all other active instances
    if instance_id == "instance_1":
        launch_all_active_instances()

    # Launch this instance
    DesktopWidget(instance_id, is_new)