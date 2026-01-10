"""
Settings Window for TimeDateWeather Desktop Widget
Provides GUI for configuring all widget settings with hybrid preview mode.
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from config_manager import ConfigManager


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
        self.window.geometry("500x650")
        self.window.resizable(False, False)

        # Position window near the widget instead of primary monitor
        widget_x = parent_widget.root.winfo_x()
        widget_y = parent_widget.root.winfo_y()
        # Offset the settings window slightly to the right and down from widget
        self.window.geometry(f"+{widget_x + 50}+{widget_y + 50}")

        # Make window modal (stays on top of widget)
        self.window.transient(parent_widget.root)
        self.window.grab_set()

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Show widget border when settings is open
        self.parent_widget.show_settings_border(True)

        # Create instance selector frame at top
        self.create_instance_selector()

        # Create tabbed interface
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self.create_location_tab()
        self.create_appearance_tab()
        self.create_spacing_tab()
        self.create_display_tab()

        # Bottom button panel
        self.create_button_panel()

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
                messagebox.showinfo("Instance Switched",
                                  f"Now editing settings for {new_instance}")

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
            messagebox.showinfo("Instance Created",
                              f"New instance {new_instance_id} created and launched!")

    def remove_current_instance(self):
        """Remove the currently selected instance."""
        current_instance = self.instance_var.get()

        # Cannot remove last instance
        if len(self.config.get_all_instances()) <= 1:
            messagebox.showwarning("Cannot Remove",
                                 "Cannot remove the last instance. At least one must remain.")
            return

        # Cannot remove currently running widget's instance
        if current_instance == self.parent_widget.instance_id:
            messagebox.showwarning("Cannot Remove",
                                 "Cannot remove the current running instance.\n"
                                 "Please switch to another instance first, or close this widget.")
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
                messagebox.showinfo("Instance Removed",
                                  f"Instance {current_instance} has been removed.")

    def reload_all_settings(self):
        """Reload all settings from the currently selected instance."""
        # This would need to reload all the UI elements with new config values
        # For now, we'll just show a message that they should reopen settings
        # A full implementation would recreate all the tabs
        pass

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

        # Info label
        info_text = "Note: Location changes require 'Apply' or 'Save' to take effect."
        ttk.Label(tab, text=info_text, font=("Segoe UI", 9), foreground="gray").grid(
            row=7, column=0, columnspan=2, sticky="w", padx=10, pady=20
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

        # Font Family
        ttk.Label(scrollable_frame, text="Font Family:", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        row += 1

        font_families = [
            "Segoe UI", "Segoe UI Black", "Segoe UI Light", "Segoe UI Semibold", "Segoe UI Semilight",
            "Arial", "Arial Black", "Arial Narrow",
            "Calibri", "Calibri Light",
            "Cambria", "Cambria Math",
            "Candara", "Candara Light",
            "Comic Sans MS",
            "Consolas",
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

        # Sound Options
        ttk.Label(tab, text="Sound:", font=("Segoe UI", 10, "bold")).grid(
            row=3, column=0, sticky="w", padx=10, pady=(20, 5)
        )

        self.hourly_chime_var = tk.BooleanVar(value=self.config.get('display', 'hourly_chime'))
        ttk.Checkbutton(tab, text="Play sound at top of each hour", variable=self.hourly_chime_var).grid(
            row=4, column=0, sticky="w", padx=10, pady=5
        )

        # Startup Options
        ttk.Label(tab, text="Startup:", font=("Segoe UI", 10, "bold")).grid(
            row=5, column=0, sticky="w", padx=10, pady=(20, 5)
        )

        self.launch_at_boot_var = tk.BooleanVar(value=self.config.get('display', 'launch_at_boot'))
        ttk.Checkbutton(tab, text="Launch at Windows Startup", variable=self.launch_at_boot_var).grid(
            row=6, column=0, sticky="w", padx=10, pady=5
        )

        # Position Info
        ttk.Label(tab, text="Position:", font=("Segoe UI", 10, "bold")).grid(
            row=7, column=0, sticky="w", padx=10, pady=(20, 5)
        )

        current_x = self.config.get('position', 'x')
        current_y = self.config.get('position', 'y')
        ttk.Label(tab, text=f"Current: X={current_x}, Y={current_y}", font=("Segoe UI", 9)).grid(
            row=8, column=0, sticky="w", padx=10, pady=5
        )

        ttk.Label(tab, text="Drag the widget to reposition.", font=("Segoe UI", 9), foreground="gray").grid(
            row=9, column=0, sticky="w", padx=10, pady=5
        )

        # Reset to Default Position button
        ttk.Button(tab, text="Reset to Default (50, 50)", command=self.reset_position).grid(
            row=10, column=0, sticky="w", padx=10, pady=10
        )

        # Info
        ttk.Label(tab, text="Format changes preview instantly.", font=("Segoe UI", 9), foreground="gray").grid(
            row=11, column=0, sticky="w", padx=10, pady=20
        )

    def create_button_panel(self):
        """Bottom button panel with Apply, Save, Cancel, Reset."""
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Apply", command=self.on_apply, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save", command=self.on_save, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset Defaults", command=self.on_reset, width=15).pack(side=tk.RIGHT, padx=5)

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

        # Update sound settings
        self.config.set('display', 'hourly_chime', self.hourly_chime_var.get())

        # Update launch at boot setting
        self.config.set('display', 'launch_at_boot', self.launch_at_boot_var.get())
        self.parent_widget.set_launch_at_boot(self.launch_at_boot_var.get())

        # Apply instant preview settings (in case not already applied)
        self.apply_instant_preview()

        # Clear status line positioning message
        self.parent_widget.status_text = ""
        self.parent_widget.update_status_ui()

        # Refresh weather with new location and format
        self.parent_widget.manual_weather_refresh()

    def on_save(self):
        """Save all settings to config file and close window."""
        # Apply all settings first
        self.on_apply()

        # Clear status line positioning message
        self.parent_widget.status_text = ""
        self.parent_widget.update_status_ui()

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
        self.parent_widget.status_text = ""
        self.parent_widget.update_status_ui()

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
            self.parent_widget.status_text = ""
            self.parent_widget.update_status_ui()

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
