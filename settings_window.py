"""
Settings Window for TimeDateWeather Desktop Widget
Provides GUI for configuring all widget settings with hybrid preview mode.
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
from config_manager import ConfigManager
from themes import THEMES, get_theme, get_theme_names, apply_theme_to_config
from notifications import ToolTip, show_toast


class SettingsWindow:
    """Lightweight settings window with tabbed interface and hybrid preview."""

    def __init__(self, parent_widget):
        """
        Initialize settings window.

        Args:
            parent_widget: Reference to main DesktopWidget instance
        """
        self.parent_widget = parent_widget
        self.config = parent_widget.config

        # Track original settings for cancel/revert
        self.original_config = self._deep_copy_config()

        # Create window
        self.window = tk.Toplevel(parent_widget.root)
        self.window.title("Widget Settings")
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        window_width = min(560, screen_width - 80)
        window_height = min(760, screen_height - 80)
        self.window.geometry(f"{window_width}x{window_height}")
        self.window.minsize(420, 520)
        self.window.resizable(True, True)

        # Position window near the widget instead of primary monitor
        widget_x = parent_widget.root.winfo_x()
        widget_y = parent_widget.root.winfo_y()
        # Offset the settings window slightly to the right and down from widget
        window_x = widget_x + 50
        window_y = widget_y + 50
        self.window.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")

        # Make window modal (stays on top of widget)
        self.window.transient(parent_widget.root)
        self.window.grab_set()
        self.window.attributes("-topmost", True)
        self.window.lift()

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Show widget border when settings is open
        self.parent_widget.show_settings_border(True)

        # Create instance selector frame at top
        self.create_instance_selector()

        # Create tabbed interface
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self.create_location_tab()
        self.create_appearance_tab()
        self.create_spacing_tab()
        self.create_display_tab()

        # Bottom button panel
        self.create_button_panel()

        # Ensure window is fully visible after layout
        self._ensure_on_screen()

    def create_instance_selector(self):
        """Create instance selector at top of settings window."""
        frame = ttk.Frame(self.window)
        frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Instance selector label and dropdown
        ttk.Label(frame, text="Widget Instance:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        # Get all instances
        all_instances = self.config.get_all_instances()
        current_instance = self.parent_widget.instance_id

        self.instance_var = tk.StringVar(value=current_instance)
        instance_combo = ttk.Combobox(frame, textvariable=self.instance_var,
                                      values=all_instances,
                                      state="readonly", width=15)
        instance_combo.pack(side=tk.LEFT, padx=(0, 10))
        instance_combo.bind("<<ComboboxSelected>>", self.on_instance_changed)

        # Add instance button
        ttk.Button(frame, text="+ New", command=self.add_new_instance, width=8).pack(side=tk.LEFT, padx=2)

        # Remove instance button
        ttk.Button(frame, text="- Remove", command=self.remove_current_instance, width=8).pack(side=tk.LEFT, padx=2)

        # Info label
        info_frame = ttk.Frame(self.window)
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(info_frame, text=f"Currently editing: {current_instance}",
                 font=("Segoe UI", 9), foreground="gray").pack(side=tk.LEFT)

    def on_instance_changed(self, event=None):
        """Handle instance selection change."""
        new_instance = self.instance_var.get()
        if new_instance != self.parent_widget.instance_id:
            # Save current instance settings first
            self.on_apply()

            # Switch to new instance
            if self.config.switch_instance(new_instance):
                # Reload all settings for new instance
                self.reload_all_settings()
                show_toast(self.window, f"Now editing {new_instance}", 2000, "info")

    def add_new_instance(self):
        """Add a new widget instance."""
        # Generate new instance ID
        all_instances = self.config.get_all_instances()
        instance_num = 1
        while f"instance_{instance_num}" in all_instances:
            instance_num += 1
        new_instance_id = f"instance_{instance_num}"

        # Add to config
        if self.config.add_instance(new_instance_id):
            # Update dropdown
            all_instances = self.config.get_all_instances()
            # Find the combobox and update its values
            for widget in self.window.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Combobox) and child['textvariable'] == str(self.instance_var):
                            child['values'] = all_instances
                            break

            # Launch the new instance
            self.parent_widget.launch_new_instance()
            show_toast(self.window, f"{new_instance_id} created and launched", 2500, "success")

    def remove_current_instance(self):
        """Remove the currently selected instance."""
        current_instance = self.instance_var.get()

        # Cannot remove last instance
        if len(self.config.get_all_instances()) <= 1:
            show_toast(self.window, "Cannot remove the last instance", 2500, "warning")
            return

        # Cannot remove currently running widget's instance
        if current_instance == self.parent_widget.instance_id:
            show_toast(self.window, "Switch to another instance before removing this one", 3000, "warning")
            return

        # Confirm removal
        response = messagebox.askyesno("Remove Instance",
                                      f"Are you sure you want to remove {current_instance}?\n"
                                      "This will delete all settings for this instance.",
                                      icon='warning')

        if response:
            if self.config.remove_instance(current_instance):
                # Update dropdown
                all_instances = self.config.get_all_instances()
                for widget in self.window.winfo_children():
                    if isinstance(widget, ttk.Frame):
                        for child in widget.winfo_children():
                            if isinstance(child, ttk.Combobox) and child['textvariable'] == str(self.instance_var):
                                child['values'] = all_instances
                                # Select first instance
                                if all_instances:
                                    self.instance_var.set(all_instances[0])
                                break
                show_toast(self.window, f"{current_instance} removed", 2500, "success")

    def reload_all_settings(self):
        """Reload all settings from the currently selected instance."""
        try:
            # Reload location settings
            self.zip_entry.delete(0, tk.END)
            self.zip_entry.insert(0, self.config.get('location', 'zip_code'))

            self.country_entry.delete(0, tk.END)
            self.country_entry.insert(0, self.config.get('location', 'country'))

            # Reload weather interval
            current_interval = self.config.get('updates', 'weather_interval') // 60000
            self.weather_interval_var.set(current_interval)

            # Reload weather display settings
            current_format = self.config.get('weather', 'display_format')
            if current_format in self.format_map_reverse:
                self.weather_format_var.set(self.format_map_reverse[current_format])

            self.show_weather_attribution_var.set(self.config.get('weather', 'show_attribution'))
            self.show_emoji_var.set(self.config.get('weather', 'show_emoji'))
            self.show_forecast_var.set(self.config.get('weather', 'show_forecast'))

            # Reload font settings
            self.font_family_var.set(self.config.get('fonts', 'family'))
            self.time_size_var.set(self.config.get('fonts', 'time_size'))
            self.date_size_var.set(self.config.get('fonts', 'date_size'))
            self.weather_size_var.set(self.config.get('fonts', 'weather_size'))

            # Reload color settings
            self.text_color_var.set(self.config.get('colors', 'text'))
            self.shadow_color_var.set(self.config.get('colors', 'shadow'))
            self.status_color_var.set(self.config.get('colors', 'status'))
            self.lock_colors_var.set(self.config.get('colors', 'lock_colors'))
            self.time_color_var.set(self.config.get('colors', 'time_color'))
            self.date_color_var.set(self.config.get('colors', 'date_color'))
            self.weather_color_var.set(self.config.get('colors', 'weather_color'))

            # Update color buttons
            self.text_color_btn.config(bg=self.text_color_var.get())
            self.shadow_color_btn.config(bg=self.shadow_color_var.get())
            self.status_color_btn.config(bg=self.status_color_var.get())
            self.time_color_btn.config(bg=self.time_color_var.get())
            self.date_color_btn.config(bg=self.date_color_var.get())
            self.weather_color_btn.config(bg=self.weather_color_var.get())

            # Reload appearance settings
            self.opacity_var.set(self.config.get('appearance', 'opacity'))
            self.scale_var.set(self.config.get('appearance', 'scale'))
            self.shadow_offset_x_var.set(self.config.get('appearance', 'shadow_offset_x'))
            self.shadow_offset_y_var.set(self.config.get('appearance', 'shadow_offset_y'))

            # Reload theme
            current_theme = self.config.get('appearance', 'theme') or 'default'
            if current_theme in THEMES:
                self.theme_var.set(THEMES[current_theme]['name'])
            else:
                self.theme_var.set('Custom')

            # Reload spacing settings
            self.status_x_var.set(self.config.get('spacing', 'status_x'))
            self.status_y_var.set(self.config.get('spacing', 'status_y'))
            self.time_x_var.set(self.config.get('spacing', 'time_x'))
            self.time_y_var.set(self.config.get('spacing', 'time_y'))
            self.date_x_var.set(self.config.get('spacing', 'date_x'))
            self.date_y_var.set(self.config.get('spacing', 'date_y'))
            self.weather_x_var.set(self.config.get('spacing', 'weather_x'))
            self.weather_y_var.set(self.config.get('spacing', 'weather_y'))
            self.center_x_var.set(self.config.get('spacing', 'time_x'))
            self.center_y_var.set(self.config.get('spacing', 'time_y'))

            # Reload display settings
            self.use_24h_var.set(self.config.get('display', 'use_24h_format'))
            self.show_seconds_var.set(self.config.get('display', 'show_seconds'))
            self.hourly_chime_var.set(self.config.get('display', 'hourly_chime'))
            self.weather_refresh_chime_var.set(self.config.get('display', 'weather_refresh_chime'))
            self.launch_at_boot_var.set(self.config.get('display', 'launch_at_boot'))
            self.snap_to_edges_var.set(self.config.get('display', 'snap_to_edges'))
            self.click_through_locked_var.set(self.config.get('display', 'click_through_locked'))

            # Reload date format
            current_date_format = self.config.get('display', 'date_format') or "%A, %B %d"
            if current_date_format in self.date_format_map_reverse:
                self.date_format_var.set(self.date_format_map_reverse[current_date_format])

            # Toggle color lock visibility
            self.toggle_color_lock()

            # Update original config for cancel
            self.original_config = self._deep_copy_config()

        except Exception:
            pass  # Silent failure

    def create_location_tab(self):
        """Location settings: ZIP code, country, weather update interval."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Location & Weather")

        # ZIP Code
        ttk.Label(tab, text="ZIP Code:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.zip_entry = ttk.Entry(tab, width=20)
        self.zip_entry.insert(0, self.config.get('location', 'zip_code'))
        self.zip_entry.grid(row=0, column=1, sticky="w", padx=10, pady=10)

        # Country
        ttk.Label(tab, text="Country:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.country_entry = ttk.Entry(tab, width=20)
        self.country_entry.insert(0, self.config.get('location', 'country'))
        self.country_entry.grid(row=1, column=1, sticky="w", padx=10, pady=10)

        # Weather Update Interval
        ttk.Label(tab, text="Weather Update (minutes):", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", padx=10, pady=10)

        interval_frame = ttk.Frame(tab)
        interval_frame.grid(row=2, column=1, sticky="w", padx=10, pady=10)

        current_interval = self.config.get('updates', 'weather_interval') // 60000  # Convert ms to minutes
        self.weather_interval_var = tk.IntVar(value=current_interval)

        # Entry field for direct input
        self.weather_interval_entry = ttk.Entry(interval_frame, width=8, textvariable=self.weather_interval_var)
        self.weather_interval_entry.pack(side=tk.LEFT, padx=(0, 10))

        self.weather_interval_slider = ttk.Scale(
            interval_frame,
            from_=5,
            to=60,
            orient=tk.HORIZONTAL,
            variable=self.weather_interval_var
        )
        self.weather_interval_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Separator
        ttk.Separator(tab, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=15)

        # Weather Display Options
        ttk.Label(tab, text="Weather Display:", font=("Segoe UI", 10, "bold")).grid(
            row=4, column=0, sticky="w", padx=10, pady=(10, 5)
        )

        # Weather Display Format
        ttk.Label(tab, text="Display Format:", font=("Segoe UI", 10)).grid(row=5, column=0, sticky="w", padx=10, pady=10)

        weather_formats = [
            ("Standard (Condition, Temp, Wind)", "standard"),
            ("Simple (Condition, Temp)", "simple"),
            ("Detailed (+ Humidity)", "detailed"),
            ("Minimal (Temp only)", "minimal")
        ]

        self.weather_format_var = tk.StringVar(value=self.config.get('weather', 'display_format'))
        format_combo = ttk.Combobox(tab, textvariable=self.weather_format_var,
                                    values=[fmt[0] for fmt in weather_formats],
                                    state="readonly", width=30)
        format_combo.grid(row=5, column=1, sticky="w", padx=10, pady=10)

        # Map display names to format keys
        self.format_map = {fmt[0]: fmt[1] for fmt in weather_formats}
        self.format_map_reverse = {fmt[1]: fmt[0] for fmt in weather_formats}

        # Set initial value
        current_format = self.config.get('weather', 'display_format')
        if current_format in self.format_map_reverse:
            format_combo.set(self.format_map_reverse[current_format])

        # Show Weather Attribution
        self.show_weather_attribution_var = tk.BooleanVar(value=self.config.get('weather', 'show_attribution'))
        ttk.Checkbutton(tab, text='Show "Weather from wttr.in" attribution',
                       variable=self.show_weather_attribution_var).grid(
            row=6, column=0, columnspan=2, sticky="w", padx=10, pady=5
        )

        # Show Weather Emoji
        self.show_emoji_var = tk.BooleanVar(value=self.config.get('weather', 'show_emoji'))
        emoji_check = ttk.Checkbutton(tab, text='Show weather emoji icons',
                       variable=self.show_emoji_var)
        emoji_check.grid(row=7, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        ToolTip(emoji_check, "Display weather condition emojis (sun, cloud, rain, etc.)")

        # Separator before forecast
        ttk.Separator(tab, orient='horizontal').grid(row=8, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        # Forecast Options
        ttk.Label(tab, text="Forecast:", font=("Segoe UI", 10, "bold")).grid(
            row=9, column=0, sticky="w", padx=10, pady=(5, 5)
        )

        self.show_forecast_var = tk.BooleanVar(value=self.config.get('weather', 'show_forecast'))
        forecast_check = ttk.Checkbutton(tab, text="Show tomorrow's forecast",
                       variable=self.show_forecast_var)
        forecast_check.grid(row=10, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        ToolTip(forecast_check, "Display both current weather and tomorrow's forecast")

        # Info label
        info_text = "Note: Location changes require 'Apply' or 'Save' to take effect."
        ttk.Label(tab, text=info_text, font=("Segoe UI", 9), foreground="gray").grid(
            row=11, column=0, columnspan=2, sticky="w", padx=10, pady=20
        )

    def create_appearance_tab(self):
        """Appearance settings: fonts, colors, opacity (instant preview)."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Appearance")

        # Create canvas for scrolling
        canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0

        # Theme Preset Selector
        ttk.Label(scrollable_frame, text="Theme Preset:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        row += 1

        theme_names = ["Custom"] + [t["name"] for t in THEMES.values()]
        current_theme = self.config.get('appearance', 'theme') or 'default'
        current_theme_name = THEMES.get(current_theme, {}).get('name', 'Custom')

        self.theme_var = tk.StringVar(value=current_theme_name)
        theme_combo = ttk.Combobox(scrollable_frame, textvariable=self.theme_var,
                                   values=theme_names, state="readonly", width=25)
        theme_combo.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        theme_combo.bind("<<ComboboxSelected>>", self.on_theme_selected)
        ToolTip(theme_combo, "Select a pre-configured color scheme")
        row += 1

        # Separator
        ttk.Separator(scrollable_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=10
        )
        row += 1

        # Font Family
        ttk.Label(scrollable_frame, text="Font Family:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        row += 1

        font_families = [
            "Segoe UI", "Segoe UI Black", "Segoe UI Light", "Segoe UI Semibold", "Segoe UI Semilight",
            "Segoe UI Variable Display", "Segoe UI Variable Text",
            "Bahnschrift", "Bahnschrift Light", "Bahnschrift SemiBold", "Bahnschrift SemiCondensed",
            "Arial", "Arial Black", "Arial Narrow",
            "Calibri", "Calibri Light",
            "Cambria", "Cambria Math",
            "Candara", "Candara Light",
            "Comic Sans MS",
            "Consolas", "Cascadia Code", "Cascadia Mono",
            "Constantia",
            "Corbel", "Corbel Light",
            "Courier", "Courier New",
            "Ebrima",
            "Franklin Gothic Medium",
            "Gabriola",
            "Gadugi",
            "Georgia",
            "Impact",
            "Ink Free",
            "Javanese Text",
            "Leelawadee UI", "Leelawadee UI Semilight",
            "Lucida Console", "Lucida Sans Unicode",
            "Malgun Gothic", "Malgun Gothic Semilight",
            "Microsoft Himalaya", "Microsoft JhengHei", "Microsoft JhengHei Light", "Microsoft New Tai Lue",
            "Microsoft PhagsPa", "Microsoft Sans Serif", "Microsoft Tai Le", "Microsoft YaHei", "Microsoft YaHei Light",
            "Microsoft Yi Baiti",
            "MingLiU-ExtB", "PMingLiU-ExtB",
            "Mongolian Baiti",
            "MS Gothic", "MS PGothic", "MS UI Gothic",
            "MV Boli",
            "Myanmar Text",
            "Nirmala UI", "Nirmala UI Semilight",
            "Palatino Linotype",
            "Roboto", "Roboto Condensed", "Roboto Light", "Roboto Medium", "Roboto Thin",
            "Segoe MDL2 Assets", "Segoe Print", "Segoe Script",
            "SimSun", "SimSun-ExtB",
            "Sitka Banner", "Sitka Display", "Sitka Heading", "Sitka Small", "Sitka Subheading", "Sitka Text",
            "Sylfaen",
            "Tahoma",
            "Times New Roman",
            "Trebuchet MS",
            "Verdana",
            "Yu Gothic", "Yu Gothic Light", "Yu Gothic Medium", "Yu Gothic UI", "Yu Gothic UI Light", "Yu Gothic UI Semibold", "Yu Gothic UI Semilight"
        ]
        self.font_family_var = tk.StringVar(value=self.config.get('fonts', 'family'))
        font_combo = ttk.Combobox(scrollable_frame, textvariable=self.font_family_var, values=font_families, state="readonly", width=25)
        font_combo.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        font_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_instant_preview())
        row += 1

        # Font Sizes
        ttk.Label(scrollable_frame, text="Font Sizes:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(15, 5)
        )
        row += 1

        # Time Size
        size_frame = ttk.Frame(scrollable_frame)
        size_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(size_frame, text="Time Size:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.time_size_var = tk.IntVar(value=self.config.get('fonts', 'time_size'))
        self.time_size_entry = ttk.Entry(size_frame, width=6, textvariable=self.time_size_var)
        self.time_size_entry.pack(side=tk.LEFT, padx=(0, 10))
        time_slider = ttk.Scale(size_frame, from_=24, to=72, orient=tk.HORIZONTAL, variable=self.time_size_var,
                                command=lambda v: self.apply_instant_preview())
        time_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Date Size
        size_frame = ttk.Frame(scrollable_frame)
        size_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(size_frame, text="Date Size:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.date_size_var = tk.IntVar(value=self.config.get('fonts', 'date_size'))
        self.date_size_entry = ttk.Entry(size_frame, width=6, textvariable=self.date_size_var)
        self.date_size_entry.pack(side=tk.LEFT, padx=(0, 10))
        date_slider = ttk.Scale(size_frame, from_=10, to=32, orient=tk.HORIZONTAL, variable=self.date_size_var,
                                command=lambda v: self.apply_instant_preview())
        date_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Weather Size
        size_frame = ttk.Frame(scrollable_frame)
        size_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(size_frame, text="Weather Size:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.weather_size_var = tk.IntVar(value=self.config.get('fonts', 'weather_size'))
        self.weather_size_entry = ttk.Entry(size_frame, width=6, textvariable=self.weather_size_var)
        self.weather_size_entry.pack(side=tk.LEFT, padx=(0, 10))
        weather_slider = ttk.Scale(size_frame, from_=10, to=32, orient=tk.HORIZONTAL, variable=self.weather_size_var,
                                   command=lambda v: self.apply_instant_preview())
        weather_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Colors
        ttk.Label(scrollable_frame, text="Colors:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(15, 5)
        )
        row += 1

        # Lock Colors Checkbox
        self.lock_colors_var = tk.BooleanVar(value=self.config.get('colors', 'lock_colors'))
        ttk.Checkbutton(scrollable_frame, text="Lock all text colors together", variable=self.lock_colors_var,
                       command=self.toggle_color_lock).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row += 1

        # Text Color (Master when locked)
        color_frame = ttk.Frame(scrollable_frame)
        color_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(color_frame, text="Text Color:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.text_color_var = tk.StringVar(value=self.config.get('colors', 'text'))
        self.text_color_entry = ttk.Entry(color_frame, textvariable=self.text_color_var, width=10)
        self.text_color_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.text_color_entry.bind("<Return>", lambda e: self.on_hex_color_change('text', self.text_color_var, self.text_color_btn))
        self.text_color_entry.bind("<FocusOut>", lambda e: self.on_hex_color_change('text', self.text_color_var, self.text_color_btn))
        self.text_color_btn = tk.Button(color_frame, bg=self.text_color_var.get(), width=3, text="...",
                                        command=lambda: self.choose_color('text', self.text_color_var, self.text_color_btn))
        self.text_color_btn.pack(side=tk.LEFT, padx=5)
        row += 1

        # Individual Line Colors (shown when unlocked)
        self.individual_colors_frame = ttk.Frame(scrollable_frame)
        self.individual_colors_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        row += 1

        # Time Color
        time_color_frame = ttk.Frame(self.individual_colors_frame)
        time_color_frame.pack(fill=tk.X, pady=2)
        ttk.Label(time_color_frame, text="  Time:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.time_color_var = tk.StringVar(value=self.config.get('colors', 'time_color'))
        self.time_color_entry = ttk.Entry(time_color_frame, textvariable=self.time_color_var, width=10)
        self.time_color_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.time_color_entry.bind("<Return>", lambda e: self.on_hex_color_change('time', self.time_color_var, self.time_color_btn))
        self.time_color_entry.bind("<FocusOut>", lambda e: self.on_hex_color_change('time', self.time_color_var, self.time_color_btn))
        self.time_color_btn = tk.Button(time_color_frame, bg=self.time_color_var.get(), width=3, text="...",
                                        command=lambda: self.choose_color('time', self.time_color_var, self.time_color_btn))
        self.time_color_btn.pack(side=tk.LEFT, padx=5)

        # Date Color
        date_color_frame = ttk.Frame(self.individual_colors_frame)
        date_color_frame.pack(fill=tk.X, pady=2)
        ttk.Label(date_color_frame, text="  Date:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.date_color_var = tk.StringVar(value=self.config.get('colors', 'date_color'))
        self.date_color_entry = ttk.Entry(date_color_frame, textvariable=self.date_color_var, width=10)
        self.date_color_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.date_color_entry.bind("<Return>", lambda e: self.on_hex_color_change('date', self.date_color_var, self.date_color_btn))
        self.date_color_entry.bind("<FocusOut>", lambda e: self.on_hex_color_change('date', self.date_color_var, self.date_color_btn))
        self.date_color_btn = tk.Button(date_color_frame, bg=self.date_color_var.get(), width=3, text="...",
                                        command=lambda: self.choose_color('date', self.date_color_var, self.date_color_btn))
        self.date_color_btn.pack(side=tk.LEFT, padx=5)

        # Weather Color
        weather_color_frame = ttk.Frame(self.individual_colors_frame)
        weather_color_frame.pack(fill=tk.X, pady=2)
        ttk.Label(weather_color_frame, text="  Weather:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.weather_color_var = tk.StringVar(value=self.config.get('colors', 'weather_color'))
        self.weather_color_entry = ttk.Entry(weather_color_frame, textvariable=self.weather_color_var, width=10)
        self.weather_color_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.weather_color_entry.bind("<Return>", lambda e: self.on_hex_color_change('weather', self.weather_color_var, self.weather_color_btn))
        self.weather_color_entry.bind("<FocusOut>", lambda e: self.on_hex_color_change('weather', self.weather_color_var, self.weather_color_btn))
        self.weather_color_btn = tk.Button(weather_color_frame, bg=self.weather_color_var.get(), width=3, text="...",
                                           command=lambda: self.choose_color('weather', self.weather_color_var, self.weather_color_btn))
        self.weather_color_btn.pack(side=tk.LEFT, padx=5)

        # Set initial visibility based on lock state
        if self.lock_colors_var.get():
            self.individual_colors_frame.grid_remove()
        row += 1

        # Shadow Color
        color_frame = ttk.Frame(scrollable_frame)
        color_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(color_frame, text="Shadow Color:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.shadow_color_var = tk.StringVar(value=self.config.get('colors', 'shadow'))
        self.shadow_color_entry = ttk.Entry(color_frame, textvariable=self.shadow_color_var, width=10)
        self.shadow_color_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.shadow_color_entry.bind("<Return>", lambda e: self.on_hex_color_change('shadow', self.shadow_color_var, self.shadow_color_btn))
        self.shadow_color_entry.bind("<FocusOut>", lambda e: self.on_hex_color_change('shadow', self.shadow_color_var, self.shadow_color_btn))
        self.shadow_color_btn = tk.Button(color_frame, bg=self.shadow_color_var.get(), width=3, text="...",
                                         command=lambda: self.choose_color('shadow', self.shadow_color_var, self.shadow_color_btn))
        self.shadow_color_btn.pack(side=tk.LEFT, padx=5)
        row += 1

        # Status Color
        color_frame = ttk.Frame(scrollable_frame)
        color_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(color_frame, text="Status Color:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.status_color_var = tk.StringVar(value=self.config.get('colors', 'status'))
        self.status_color_entry = ttk.Entry(color_frame, textvariable=self.status_color_var, width=10)
        self.status_color_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.status_color_entry.bind("<Return>", lambda e: self.on_hex_color_change('status', self.status_color_var, self.status_color_btn))
        self.status_color_entry.bind("<FocusOut>", lambda e: self.on_hex_color_change('status', self.status_color_var, self.status_color_btn))
        self.status_color_btn = tk.Button(color_frame, bg=self.status_color_var.get(), width=3, text="...",
                                         command=lambda: self.choose_color('status', self.status_color_var, self.status_color_btn))
        self.status_color_btn.pack(side=tk.LEFT, padx=5)
        row += 1

        # Opacity
        ttk.Label(scrollable_frame, text="Opacity:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(15, 5)
        )
        row += 1

        opacity_frame = ttk.Frame(scrollable_frame)
        opacity_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        self.opacity_var = tk.DoubleVar(value=self.config.get('appearance', 'opacity'))
        self.opacity_entry = ttk.Entry(opacity_frame, textvariable=self.opacity_var, width=8)
        self.opacity_entry.pack(side=tk.LEFT, padx=(0, 10))

        opacity_slider = ttk.Scale(opacity_frame, from_=0.3, to=1.0, orient=tk.HORIZONTAL, variable=self.opacity_var,
                                   command=lambda v: self.apply_instant_preview())
        opacity_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Scale
        ttk.Label(scrollable_frame, text="Overall Scale:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(15, 5)
        )
        row += 1

        scale_frame = ttk.Frame(scrollable_frame)
        scale_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        self.scale_var = tk.DoubleVar(value=self.config.get('appearance', 'scale'))
        self.scale_entry = ttk.Entry(scale_frame, textvariable=self.scale_var, width=8)
        self.scale_entry.pack(side=tk.LEFT, padx=(0, 10))

        scale_slider = ttk.Scale(scale_frame, from_=0.5, to=3.0, orient=tk.HORIZONTAL, variable=self.scale_var,
                                command=lambda v: self.apply_instant_preview())
        scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ToolTip(scale_slider, "Overall widget size multiplier (0.5 = half size, 2.0 = double size)")
        row += 1

        # Shadow Offset
        ttk.Label(scrollable_frame, text="Shadow Offset:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(15, 5)
        )
        row += 1

        # Shadow X Offset
        shadow_x_frame = ttk.Frame(scrollable_frame)
        shadow_x_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(shadow_x_frame, text="Shadow X:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.shadow_offset_x_var = tk.IntVar(value=self.config.get('appearance', 'shadow_offset_x'))
        shadow_x_entry = ttk.Entry(shadow_x_frame, textvariable=self.shadow_offset_x_var, width=6)
        shadow_x_entry.pack(side=tk.LEFT, padx=(0, 10))
        shadow_x_slider = ttk.Scale(shadow_x_frame, from_=0, to=10, orient=tk.HORIZONTAL,
                                    variable=self.shadow_offset_x_var,
                                    command=lambda v: self.apply_instant_preview())
        shadow_x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ToolTip(shadow_x_slider, "Horizontal shadow offset (pixels)")
        row += 1

        # Shadow Y Offset
        shadow_y_frame = ttk.Frame(scrollable_frame)
        shadow_y_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(shadow_y_frame, text="Shadow Y:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.shadow_offset_y_var = tk.IntVar(value=self.config.get('appearance', 'shadow_offset_y'))
        shadow_y_entry = ttk.Entry(shadow_y_frame, textvariable=self.shadow_offset_y_var, width=6)
        shadow_y_entry.pack(side=tk.LEFT, padx=(0, 10))
        shadow_y_slider = ttk.Scale(shadow_y_frame, from_=0, to=10, orient=tk.HORIZONTAL,
                                    variable=self.shadow_offset_y_var,
                                    command=lambda v: self.apply_instant_preview())
        shadow_y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ToolTip(shadow_y_slider, "Vertical shadow offset (pixels)")
        row += 1

        # Info label
        info_text = "Changes preview instantly on the widget."
        ttk.Label(scrollable_frame, text=info_text, font=("Segoe UI", 9), foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=20
        )

    def create_spacing_tab(self):
        """Spacing settings: X and Y positions of each line (instant preview)."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Spacing")

        # Create canvas for scrolling
        canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0

        # Center Position Controls
        ttk.Label(scrollable_frame, text="Center Position:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        row += 1

        ttk.Label(scrollable_frame, text="Move all elements together from center point.", font=("Segoe UI", 9), foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10)
        )
        row += 1

        # Calculate initial center (use time position as reference)
        self.center_x_var = tk.IntVar(value=self.config.get('spacing', 'time_x'))
        self.center_y_var = tk.IntVar(value=self.config.get('spacing', 'time_y'))

        # Center X
        center_x_frame = ttk.Frame(scrollable_frame)
        center_x_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(center_x_frame, text="Center X:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.center_x_entry = ttk.Entry(center_x_frame, textvariable=self.center_x_var, width=8)
        self.center_x_entry.pack(side=tk.LEFT, padx=(0, 10))
        center_x_slider = ttk.Scale(center_x_frame, from_=-100, to=500, orient=tk.HORIZONTAL, variable=self.center_x_var,
                                    command=lambda v: self.on_center_change())
        center_x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Center Y
        center_y_frame = ttk.Frame(scrollable_frame)
        center_y_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(center_y_frame, text="Center Y:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.center_y_entry = ttk.Entry(center_y_frame, textvariable=self.center_y_var, width=8)
        self.center_y_entry.pack(side=tk.LEFT, padx=(0, 10))
        center_y_slider = ttk.Scale(center_y_frame, from_=-100, to=300, orient=tk.HORIZONTAL, variable=self.center_y_var,
                                    command=lambda v: self.on_center_change())
        center_y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Separator
        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1

        # Individual Line Positions header
        ttk.Label(scrollable_frame, text="Individual Positions:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        row += 1

        ttk.Label(scrollable_frame, text="Fine-tune each line position independently.", font=("Segoe UI", 9), foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 15)
        )
        row += 1

        # Status Line X Position
        status_x_frame = ttk.Frame(scrollable_frame)
        status_x_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(status_x_frame, text="Status X:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.status_x_var = tk.IntVar(value=self.config.get('spacing', 'status_x'))
        self.status_x_entry = ttk.Entry(status_x_frame, textvariable=self.status_x_var, width=8)
        self.status_x_entry.pack(side=tk.LEFT, padx=(0, 10))
        status_x_slider = ttk.Scale(status_x_frame, from_=-100, to=500, orient=tk.HORIZONTAL, variable=self.status_x_var,
                                    command=lambda v: self.on_spacing_change('status_x', v))
        status_x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Status Line Y Position
        status_y_frame = ttk.Frame(scrollable_frame)
        status_y_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(status_y_frame, text="Status Y:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.status_y_var = tk.IntVar(value=self.config.get('spacing', 'status_y'))
        self.status_y_entry = ttk.Entry(status_y_frame, textvariable=self.status_y_var, width=8)
        self.status_y_entry.pack(side=tk.LEFT, padx=(0, 10))
        status_y_slider = ttk.Scale(status_y_frame, from_=-100, to=300, orient=tk.HORIZONTAL, variable=self.status_y_var,
                                    command=lambda v: self.on_spacing_change('status_y', v))
        status_y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Time Line X Position
        time_x_frame = ttk.Frame(scrollable_frame)
        time_x_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(time_x_frame, text="Time X:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.time_x_var = tk.IntVar(value=self.config.get('spacing', 'time_x'))
        self.time_x_entry = ttk.Entry(time_x_frame, textvariable=self.time_x_var, width=8)
        self.time_x_entry.pack(side=tk.LEFT, padx=(0, 10))
        time_x_slider = ttk.Scale(time_x_frame, from_=-100, to=500, orient=tk.HORIZONTAL, variable=self.time_x_var,
                                  command=lambda v: self.on_spacing_change('time_x', v))
        time_x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Time Line Y Position
        time_y_frame = ttk.Frame(scrollable_frame)
        time_y_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(time_y_frame, text="Time Y:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.time_y_var = tk.IntVar(value=self.config.get('spacing', 'time_y'))
        self.time_y_entry = ttk.Entry(time_y_frame, textvariable=self.time_y_var, width=8)
        self.time_y_entry.pack(side=tk.LEFT, padx=(0, 10))
        time_y_slider = ttk.Scale(time_y_frame, from_=-100, to=300, orient=tk.HORIZONTAL, variable=self.time_y_var,
                                  command=lambda v: self.on_spacing_change('time_y', v))
        time_y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Date Line X Position
        date_x_frame = ttk.Frame(scrollable_frame)
        date_x_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(date_x_frame, text="Date X:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.date_x_var = tk.IntVar(value=self.config.get('spacing', 'date_x'))
        self.date_x_entry = ttk.Entry(date_x_frame, textvariable=self.date_x_var, width=8)
        self.date_x_entry.pack(side=tk.LEFT, padx=(0, 10))
        date_x_slider = ttk.Scale(date_x_frame, from_=-100, to=500, orient=tk.HORIZONTAL, variable=self.date_x_var,
                                  command=lambda v: self.on_spacing_change('date_x', v))
        date_x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Date Line Y Position
        date_y_frame = ttk.Frame(scrollable_frame)
        date_y_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(date_y_frame, text="Date Y:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.date_y_var = tk.IntVar(value=self.config.get('spacing', 'date_y'))
        self.date_y_entry = ttk.Entry(date_y_frame, textvariable=self.date_y_var, width=8)
        self.date_y_entry.pack(side=tk.LEFT, padx=(0, 10))
        date_y_slider = ttk.Scale(date_y_frame, from_=-100, to=300, orient=tk.HORIZONTAL, variable=self.date_y_var,
                                  command=lambda v: self.on_spacing_change('date_y', v))
        date_y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Weather Line X Position
        weather_x_frame = ttk.Frame(scrollable_frame)
        weather_x_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(weather_x_frame, text="Weather X:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.weather_x_var = tk.IntVar(value=self.config.get('spacing', 'weather_x'))
        self.weather_x_entry = ttk.Entry(weather_x_frame, textvariable=self.weather_x_var, width=8)
        self.weather_x_entry.pack(side=tk.LEFT, padx=(0, 10))
        weather_x_slider = ttk.Scale(weather_x_frame, from_=-100, to=500, orient=tk.HORIZONTAL, variable=self.weather_x_var,
                                     command=lambda v: self.on_spacing_change('weather_x', v))
        weather_x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Weather Line Y Position
        weather_y_frame = ttk.Frame(scrollable_frame)
        weather_y_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(weather_y_frame, text="Weather Y:", font=("Segoe UI", 9), width=12).pack(side=tk.LEFT)
        self.weather_y_var = tk.IntVar(value=self.config.get('spacing', 'weather_y'))
        self.weather_y_entry = ttk.Entry(weather_y_frame, textvariable=self.weather_y_var, width=8)
        self.weather_y_entry.pack(side=tk.LEFT, padx=(0, 10))
        weather_y_slider = ttk.Scale(weather_y_frame, from_=-100, to=300, orient=tk.HORIZONTAL, variable=self.weather_y_var,
                                     command=lambda v: self.on_spacing_change('weather_y', v))
        weather_y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row += 1

        # Info label
        info_text = "Changes preview instantly on the widget."
        ttk.Label(scrollable_frame, text=info_text, font=("Segoe UI", 9), foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=20
        )

    def create_display_tab(self):
        """Display settings: time format, show seconds, position (instant preview for format)."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Display")

        # Time Format Options
        ttk.Label(tab, text="Time Format:", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5)
        )

        self.use_24h_var = tk.BooleanVar(value=self.config.get('display', 'use_24h_format'))
        ttk.Checkbutton(tab, text="Use 24-Hour Format", variable=self.use_24h_var,
                       command=self.apply_instant_preview).grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self.show_seconds_var = tk.BooleanVar(value=self.config.get('display', 'show_seconds'))
        ttk.Checkbutton(tab, text="Show Seconds", variable=self.show_seconds_var,
                       command=self.apply_instant_preview).grid(row=2, column=0, sticky="w", padx=10, pady=5)

        # Date Format Options
        ttk.Label(tab, text="Date Format:", font=("Segoe UI", 10, "bold")).grid(
            row=3, column=0, sticky="w", padx=10, pady=(20, 5)
        )

        date_formats = [
            ("Full (Saturday, January 11)", "%A, %B %d"),
            ("Short (Sat, Jan 11)", "%a, %b %d"),
            ("Numeric (01/11/2025)", "%m/%d/%Y"),
            ("ISO (2025-01-11)", "%Y-%m-%d"),
            ("European (11 January 2025)", "%d %B %Y"),
            ("Minimal (Jan 11)", "%b %d")
        ]

        self.date_format_map = {fmt[0]: fmt[1] for fmt in date_formats}
        self.date_format_map_reverse = {fmt[1]: fmt[0] for fmt in date_formats}

        current_date_format = self.config.get('display', 'date_format') or "%A, %B %d"
        current_format_name = self.date_format_map_reverse.get(current_date_format, date_formats[0][0])

        self.date_format_var = tk.StringVar(value=current_format_name)
        date_format_combo = ttk.Combobox(tab, textvariable=self.date_format_var,
                                         values=[fmt[0] for fmt in date_formats],
                                         state="readonly", width=30)
        date_format_combo.grid(row=4, column=0, sticky="w", padx=10, pady=5)
        date_format_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_instant_preview())
        ToolTip(date_format_combo, "Choose how the date is displayed")

        # Sound Options
        ttk.Label(tab, text="Sound:", font=("Segoe UI", 10, "bold")).grid(
            row=5, column=0, sticky="w", padx=10, pady=(20, 5)
        )

        self.hourly_chime_var = tk.BooleanVar(value=self.config.get('display', 'hourly_chime'))
        ttk.Checkbutton(tab, text="Play sound at top of each hour", variable=self.hourly_chime_var).grid(
            row=6, column=0, sticky="w", padx=10, pady=5
        )

        self.weather_refresh_chime_var = tk.BooleanVar(value=self.config.get('display', 'weather_refresh_chime'))
        ttk.Checkbutton(tab, text="Play sound when weather refreshes", variable=self.weather_refresh_chime_var).grid(
            row=7, column=0, sticky="w", padx=10, pady=5
        )

        # Behavior Options
        ttk.Label(tab, text="Behavior:", font=("Segoe UI", 10, "bold")).grid(
            row=8, column=0, sticky="w", padx=10, pady=(20, 5)
        )

        self.snap_to_edges_var = tk.BooleanVar(value=self.config.get('display', 'snap_to_edges'))
        snap_check = ttk.Checkbutton(tab, text="Snap to screen edges", variable=self.snap_to_edges_var)
        snap_check.grid(row=9, column=0, sticky="w", padx=10, pady=5)
        ToolTip(snap_check, "Widget snaps to screen edges when dragged nearby")

        self.click_through_locked_var = tk.BooleanVar(value=self.config.get('display', 'click_through_locked'))
        click_through_check = ttk.Checkbutton(tab, text="Click-through when locked", variable=self.click_through_locked_var)
        click_through_check.grid(row=10, column=0, sticky="w", padx=10, pady=5)
        ToolTip(click_through_check, "Let clicks pass through the widget when position is locked")

        # Startup Options
        ttk.Label(tab, text="Startup:", font=("Segoe UI", 10, "bold")).grid(
            row=11, column=0, sticky="w", padx=10, pady=(20, 5)
        )

        self.launch_at_boot_var = tk.BooleanVar(value=self.config.get('display', 'launch_at_boot'))
        ttk.Checkbutton(tab, text="Launch at Windows Startup", variable=self.launch_at_boot_var).grid(
            row=12, column=0, sticky="w", padx=10, pady=5
        )

        # Position Info
        ttk.Label(tab, text="Position:", font=("Segoe UI", 10, "bold")).grid(
            row=13, column=0, sticky="w", padx=10, pady=(20, 5)
        )

        current_x = self.config.get('position', 'x')
        current_y = self.config.get('position', 'y')
        ttk.Label(tab, text=f"Current: X={current_x}, Y={current_y}", font=("Segoe UI", 9)).grid(
            row=14, column=0, sticky="w", padx=10, pady=5
        )

        ttk.Label(tab, text="Drag the widget to reposition.", font=("Segoe UI", 9), foreground="gray").grid(
            row=15, column=0, sticky="w", padx=10, pady=5
        )

        # Reset to Default Position button
        ttk.Button(tab, text="Reset to Default (50, 50)", command=self.reset_position).grid(
            row=16, column=0, sticky="w", padx=10, pady=10
        )

        # Info
        ttk.Label(tab, text="Format changes preview instantly.", font=("Segoe UI", 9), foreground="gray").grid(
            row=17, column=0, sticky="w", padx=10, pady=20
        )

    def create_button_panel(self):
        """Bottom button panel with Apply, Save, Cancel, Reset, Import, Export."""
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        # Left side - main actions
        ttk.Button(button_frame, text="Apply", command=self.on_apply, width=10).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="Save", command=self.on_save, width=10).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel, width=10).pack(side=tk.LEFT, padx=3)

        # Right side - utility actions
        ttk.Sizegrip(button_frame).pack(side=tk.RIGHT, padx=3)
        ttk.Button(button_frame, text="Reset", command=self.on_reset, width=8).pack(side=tk.RIGHT, padx=3)
        ttk.Button(button_frame, text="Export...", command=self.export_settings, width=10).pack(side=tk.RIGHT, padx=3)
        ttk.Button(button_frame, text="Import...", command=self.import_settings, width=10).pack(side=tk.RIGHT, padx=3)

    def _ensure_on_screen(self):
        """Keep the settings window fully visible."""
        try:
            self.window.update_idletasks()
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            window_width = self.window.winfo_width()
            window_height = self.window.winfo_height()
            x = self.window.winfo_x()
            y = self.window.winfo_y()
            margin = 20

            if x + window_width > screen_width - margin:
                x = max(margin, screen_width - window_width - margin)
            if y + window_height > screen_height - margin:
                y = max(margin, screen_height - window_height - margin)
            if x < margin:
                x = margin
            if y < margin:
                y = margin

            self.window.geometry(f"+{x}+{y}")
        except Exception:
            pass

    # ==========================================
    #           EVENT HANDLERS
    # ==========================================

    def toggle_color_lock(self):
        """Toggle individual color controls visibility."""
        if self.lock_colors_var.get():
            # Hide individual colors
            self.individual_colors_frame.grid_remove()
            # Sync all individual colors to master text color
            master_color = self.text_color_var.get()
            self.time_color_var.set(master_color)
            self.date_color_var.set(master_color)
            self.weather_color_var.set(master_color)
            self.time_color_btn.config(bg=master_color)
            self.date_color_btn.config(bg=master_color)
            self.weather_color_btn.config(bg=master_color)
        else:
            # Show individual colors
            self.individual_colors_frame.grid()

        self.apply_instant_preview()

    def on_hex_color_change(self, color_type, color_var, button):
        """Handle hex color entry changes with validation."""
        hex_value = color_var.get().strip()

        # Validate hex color format
        if hex_value.startswith('#') and len(hex_value) == 7:
            try:
                # Test if it's a valid hex color
                int(hex_value[1:], 16)
                button.config(bg=hex_value)

                # If colors are locked and text color changes, sync to all
                if color_type == 'text' and self.lock_colors_var.get():
                    self.time_color_var.set(hex_value)
                    self.date_color_var.set(hex_value)
                    self.weather_color_var.set(hex_value)
                    self.time_color_btn.config(bg=hex_value)
                    self.date_color_btn.config(bg=hex_value)
                    self.weather_color_btn.config(bg=hex_value)

                self.apply_instant_preview()
            except ValueError:
                pass  # Invalid hex, ignore
        elif not hex_value.startswith('#') and len(hex_value) == 6:
            # Auto-add # prefix
            hex_value = '#' + hex_value
            try:
                int(hex_value[1:], 16)
                color_var.set(hex_value)
                button.config(bg=hex_value)

                # If colors are locked and text color changes, sync to all
                if color_type == 'text' and self.lock_colors_var.get():
                    self.time_color_var.set(hex_value)
                    self.date_color_var.set(hex_value)
                    self.weather_color_var.set(hex_value)
                    self.time_color_btn.config(bg=hex_value)
                    self.date_color_btn.config(bg=hex_value)
                    self.weather_color_btn.config(bg=hex_value)

                self.apply_instant_preview()
            except ValueError:
                pass

    def on_center_change(self):
        """Handle center position changes - moves all elements together."""
        # Calculate the offset from previous center
        new_center_x = self.center_x_var.get()
        new_center_y = self.center_y_var.get()

        # Get current time position (our reference point)
        old_center_x = self.config.get('spacing', 'time_x')
        old_center_y = self.config.get('spacing', 'time_y')

        # Calculate deltas
        delta_x = new_center_x - old_center_x
        delta_y = new_center_y - old_center_y

        # Update all positions
        self.status_x_var.set(self.status_x_var.get() + delta_x)
        self.status_y_var.set(self.status_y_var.get() + delta_y)
        self.time_x_var.set(new_center_x)
        self.time_y_var.set(new_center_y)
        self.date_x_var.set(self.date_x_var.get() + delta_x)
        self.date_y_var.set(self.date_y_var.get() + delta_y)
        self.weather_x_var.set(self.weather_x_var.get() + delta_x)
        self.weather_y_var.set(self.weather_y_var.get() + delta_y)

        self.apply_instant_preview()

    def on_spacing_change(self, line_type, value):
        """Handle spacing slider changes (instant preview)."""
        # Make status line visible when adjusting status position
        if line_type in ['status_x', 'status_y']:
            self.parent_widget.status_text = "[POSITIONING] Adjusting status line position"
            self.parent_widget.update_status_ui()

        self.apply_instant_preview()

    def choose_color(self, color_type, color_var, button):
        """Open color picker and apply color (instant preview)."""
        color = colorchooser.askcolor(title=f"Choose {color_type.title()} Color", initialcolor=color_var.get())
        if color[1]:  # color[1] is hex value
            color_var.set(color[1])
            button.config(bg=color[1])

            # If colors are locked and text color changes, sync to all
            if color_type == 'text' and self.lock_colors_var.get():
                self.time_color_var.set(color[1])
                self.date_color_var.set(color[1])
                self.weather_color_var.set(color[1])
                self.time_color_btn.config(bg=color[1])
                self.date_color_btn.config(bg=color[1])
                self.weather_color_btn.config(bg=color[1])

            self.apply_instant_preview()

    def reset_position(self):
        """Reset widget position to default (50, 50)."""
        self.parent_widget.root.geometry("+50+50")
        self.parent_widget.position_changed_since_save = True

    def apply_instant_preview(self):
        """Apply instant preview for appearance settings (hybrid mode)."""
        # Update config temporarily (not saved to file yet)
        self.config.set('fonts', 'family', self.font_family_var.get())
        self.config.set('fonts', 'time_size', self.time_size_var.get())
        self.config.set('fonts', 'date_size', self.date_size_var.get())
        self.config.set('fonts', 'weather_size', self.weather_size_var.get())

        self.config.set('colors', 'text', self.text_color_var.get())
        self.config.set('colors', 'shadow', self.shadow_color_var.get())
        self.config.set('colors', 'status', self.status_color_var.get())
        self.config.set('colors', 'lock_colors', self.lock_colors_var.get())
        self.config.set('colors', 'time_color', self.time_color_var.get())
        self.config.set('colors', 'date_color', self.date_color_var.get())
        self.config.set('colors', 'weather_color', self.weather_color_var.get())

        self.config.set('appearance', 'opacity', self.opacity_var.get())
        self.config.set('appearance', 'scale', self.scale_var.get())
        self.config.set('appearance', 'shadow_offset_x', self.shadow_offset_x_var.get())
        self.config.set('appearance', 'shadow_offset_y', self.shadow_offset_y_var.get())

        self.config.set('spacing', 'status_x', self.status_x_var.get())
        self.config.set('spacing', 'status_y', self.status_y_var.get())
        self.config.set('spacing', 'time_x', self.time_x_var.get())
        self.config.set('spacing', 'time_y', self.time_y_var.get())
        self.config.set('spacing', 'date_x', self.date_x_var.get())
        self.config.set('spacing', 'date_y', self.date_y_var.get())
        self.config.set('spacing', 'weather_x', self.weather_x_var.get())
        self.config.set('spacing', 'weather_y', self.weather_y_var.get())

        self.config.set('display', 'use_24h_format', self.use_24h_var.get())
        self.config.set('display', 'show_seconds', self.show_seconds_var.get())
        self.config.set('display', 'snap_to_edges', self.snap_to_edges_var.get())
        self.config.set('display', 'click_through_locked', self.click_through_locked_var.get())

        # Update date format
        selected_date_format = self.date_format_var.get()
        if selected_date_format in self.date_format_map:
            self.config.set('display', 'date_format', self.date_format_map[selected_date_format])

        # Refresh widget display
        self.parent_widget.apply_settings()

    def on_apply(self):
        """Apply all settings including location (manual apply settings)."""
        # Update location settings
        self.config.set('location', 'zip_code', self.zip_entry.get())
        self.config.set('location', 'country', self.country_entry.get())

        # Update weather interval (convert minutes to milliseconds)
        weather_interval_ms = self.weather_interval_var.get() * 60000
        self.config.set('updates', 'weather_interval', weather_interval_ms)

        # Update weather display settings
        selected_format_name = self.weather_format_var.get()
        if selected_format_name in self.format_map:
            self.config.set('weather', 'display_format', self.format_map[selected_format_name])
        self.config.set('weather', 'show_attribution', self.show_weather_attribution_var.get())
        self.config.set('weather', 'show_emoji', self.show_emoji_var.get())
        self.config.set('weather', 'show_forecast', self.show_forecast_var.get())

        # Update sound settings
        self.config.set('display', 'hourly_chime', self.hourly_chime_var.get())
        self.config.set('display', 'weather_refresh_chime', self.weather_refresh_chime_var.get())

        # Update click-through and startup settings
        self.config.set('display', 'click_through_locked', self.click_through_locked_var.get())
        self.config.set('display', 'launch_at_boot', self.launch_at_boot_var.get())
        self.parent_widget.set_launch_at_boot(self.launch_at_boot_var.get())

        # Apply instant preview settings (in case not already applied)
        self.apply_instant_preview()

        # Clear status line positioning message
        self.parent_widget.clear_status_message()

        # Refresh weather with new location and format
        self.parent_widget.manual_weather_refresh()

    def on_save(self):
        """Save all settings to config file and close window."""
        # Apply all settings first
        self.on_apply()

        # Clear status line positioning message
        self.parent_widget.clear_status_message()

        # Hide settings border
        self.parent_widget.show_settings_border(False)

        # Save to file
        self.config.save()
        self.window.destroy()

    def on_cancel(self):
        """Cancel changes and revert to original settings."""
        # Restore original config
        self.config.config = self.original_config
        self.parent_widget.apply_settings()

        # Clear status line positioning message
        self.parent_widget.clear_status_message()

        # Hide settings border
        self.parent_widget.show_settings_border(False)

        self.window.destroy()

    def on_reset(self):
        """Reset all settings to default values."""
        response = messagebox.askyesno(
            "Reset to Defaults",
            "Are you sure you want to reset ALL settings to default values?",
            icon='warning'
        )

        if response:
            self.config.reset_to_defaults()
            self.parent_widget.apply_settings()

            # Clear status line positioning message
            self.parent_widget.clear_status_message()

            # Hide settings border
            self.parent_widget.show_settings_border(False)

            self.window.destroy()

    def _deep_copy_config(self):
        """Create a deep copy of current config for cancel/revert."""
        config_dict = self.config.get_all()
        return self._deep_copy_dict(config_dict)

    def _deep_copy_dict(self, obj):
        """Simple deep copy for nested dictionaries."""
        if isinstance(obj, dict):
            return {k: self._deep_copy_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy_dict(item) for item in obj]
        else:
            return obj

    def on_theme_selected(self, event=None):
        """Handle theme selection from dropdown."""
        selected_name = self.theme_var.get()

        if selected_name == "Custom":
            return  # Don't apply anything for Custom

        # Find theme ID by name
        theme_id = None
        for tid, theme in THEMES.items():
            if theme["name"] == selected_name:
                theme_id = tid
                break

        if theme_id:
            # Apply theme to config
            apply_theme_to_config(self.config, theme_id)

            # Update UI variables to match theme
            theme = get_theme(theme_id)

            # Update color variables
            if "colors" in theme:
                self.text_color_var.set(theme["colors"].get("text", "#ffffff"))
                self.shadow_color_var.set(theme["colors"].get("shadow", "#000000"))
                self.status_color_var.set(theme["colors"].get("status", "#808080"))
                self.time_color_var.set(theme["colors"].get("time_color", "#ffffff"))
                self.date_color_var.set(theme["colors"].get("date_color", "#ffffff"))
                self.weather_color_var.set(theme["colors"].get("weather_color", "#ffffff"))

                # Update color buttons
                self.text_color_btn.config(bg=self.text_color_var.get())
                self.shadow_color_btn.config(bg=self.shadow_color_var.get())
                self.status_color_btn.config(bg=self.status_color_var.get())
                self.time_color_btn.config(bg=self.time_color_var.get())
                self.date_color_btn.config(bg=self.date_color_var.get())
                self.weather_color_btn.config(bg=self.weather_color_var.get())

            # Update font family
            if "fonts" in theme:
                self.font_family_var.set(theme["fonts"].get("family", "Segoe UI"))

            # Update opacity
            if "appearance" in theme:
                self.opacity_var.set(theme["appearance"].get("opacity", 1.0))

            # Apply preview
            self.apply_instant_preview()

    def export_settings(self):
        """Export current settings to a JSON file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Settings",
            initialfile="timedateweather_settings.json"
        )

        if filepath:
            if self.config.export_settings(filepath):
                show_toast(self.window, "Settings exported successfully!", 2000, "success")
            else:
                show_toast(self.window, "Failed to export settings", 2000, "error")

    def import_settings(self):
        """Import settings from a JSON file."""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Settings"
        )

        if filepath:
            if self.config.import_settings(filepath):
                # Reload all UI elements with new config
                self.reload_all_settings()
                # Apply changes to widget
                self.parent_widget.apply_settings()
                show_toast(self.window, "Settings imported successfully!", 2000, "success")
            else:
                show_toast(self.window, "Failed to import settings", 2000, "error")
