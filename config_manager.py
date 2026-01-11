"""
Configuration Manager for Desktop Widget
Handles loading, saving, and validating settings from JSON file.
"""

import json
import os

# Default configuration for a single instance
DEFAULT_INSTANCE_CONFIG = {
    "location": {
        "zip_code": "80701",
        "country": "US"
    },
    "weather": {
        "show_attribution": True,
        "display_format": "standard",  # standard, simple, detailed, minimal
        "format_strings": {
            "standard": "%C+%t+%w",
            "simple": "%C+%t",
            "detailed": "%C+%t+|+%w+|+%h",
            "minimal": "%t"
        },
        "show_emoji": True,
        "show_forecast": False,
        "forecast_days": 1
    },
    "fonts": {
        "family": "Segoe UI",
        "time_size": 48,
        "date_size": 16,
        "weather_size": 16,
        "status_size": 11
    },
    "colors": {
        "text": "#ffffff",
        "status": "#808080",
        "shadow": "#000000",
        "lock_colors": True,
        "time_color": "#ffffff",
        "date_color": "#ffffff",
        "weather_color": "#ffffff"
    },
    "appearance": {
        "opacity": 1.0,
        "scale": 1.0,
        "shadow_offset_x": 2,
        "shadow_offset_y": 2,
        "theme": "default"
    },
    "display": {
        "use_24h_format": False,
        "show_seconds": False,
        "launch_at_boot": False,
        "hourly_chime": False,
        "date_format": "%A, %B %d",
        "snap_to_edges": True,
        "snap_distance": 15
    },
    "spacing": {
        "status_x": 0,
        "status_y": 0,
        "time_x": 0,
        "time_y": 18,
        "date_x": 0,
        "date_y": 75,
        "weather_x": 0,
        "weather_y": 100
    },
    "position": {
        "x": 50,
        "y": 50
    },
    "updates": {
        "time_interval": 1000,      # milliseconds
        "weather_interval": 1800000  # milliseconds (30 minutes)
    },
    "ui": {
        "settings_border_color": "#ffff00",
        "new_instance_color": "#00ff00",
        "new_instance_color_dim": "#00aa00"
    }
}

CONFIG_FILE = "settings.json"

# Root config structure with instances
DEFAULT_ROOT_CONFIG = {
    "active_instances": ["instance_1"],  # List of active instance IDs
    "instances": {
        "instance_1": DEFAULT_INSTANCE_CONFIG
    }
}


class ConfigManager:
    """Lightweight configuration manager with support for multiple instances."""

    def __init__(self, config_file=CONFIG_FILE, instance_id="instance_1"):
        self.config_file = config_file
        self.instance_id = instance_id
        self.root_config = None
        self.config = None
        self.load()

    def load(self):
        """Load configuration from JSON file. Uses defaults if file doesn't exist."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.root_config = json.load(f)

                # Migrate old config format to new instance-based format
                if "instances" not in self.root_config:
                    self.root_config = self._migrate_to_instances(self.root_config)

                # Ensure instance exists
                if self.instance_id not in self.root_config.get("instances", {}):
                    self.root_config["instances"][self.instance_id] = self._deep_copy(DEFAULT_INSTANCE_CONFIG)

                # Load this instance's config
                self.config = self._merge_with_defaults(
                    self.root_config["instances"][self.instance_id],
                    DEFAULT_INSTANCE_CONFIG
                )
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file ({e}). Using defaults.")
                self.root_config = self._deep_copy(DEFAULT_ROOT_CONFIG)
                self.config = self._deep_copy(DEFAULT_INSTANCE_CONFIG)
        else:
            # First run - use defaults
            self.root_config = self._deep_copy(DEFAULT_ROOT_CONFIG)
            self.config = self._deep_copy(DEFAULT_INSTANCE_CONFIG)
            self.save()  # Create the file with defaults

    def _migrate_to_instances(self, old_config):
        """Migrate old single-instance config to new multi-instance format."""
        return {
            "active_instances": ["instance_1"],
            "instances": {
                "instance_1": old_config
            }
        }

    def save(self):
        """Save current configuration to JSON file."""
        try:
            # Update this instance's config in root
            self.root_config["instances"][self.instance_id] = self.config

            with open(self.config_file, 'w') as f:
                json.dump(self.root_config, f, indent=4)
            return True
        except IOError as e:
            print(f"Error: Could not save config file ({e}).")
            return False

    def get(self, category, key=None):
        """
        Get configuration value.
        Usage:
            get('location', 'zip_code') -> returns "80701"
            get('location') -> returns entire location dict
        """
        if key is None:
            return self.config.get(category, {})
        return self.config.get(category, {}).get(key)

    def set(self, category, key, value):
        """
        Set configuration value.
        Usage: set('location', 'zip_code', '90210')
        """
        if category not in self.config:
            self.config[category] = {}
        self.config[category][key] = value

    def get_all(self):
        """Get entire configuration dictionary."""
        return self.config

    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self.config = self._deep_copy(DEFAULT_INSTANCE_CONFIG)
        self.save()

    def get_all_instances(self):
        """Get list of all instance IDs."""
        return list(self.root_config.get("instances", {}).keys())

    def get_active_instances(self):
        """Get list of active instance IDs."""
        return self.root_config.get("active_instances", [])

    def add_instance(self, instance_id):
        """Add a new instance with default config."""
        if instance_id not in self.root_config["instances"]:
            self.root_config["instances"][instance_id] = self._deep_copy(DEFAULT_INSTANCE_CONFIG)
            if instance_id not in self.root_config["active_instances"]:
                self.root_config["active_instances"].append(instance_id)
            self.save()
            return True
        return False

    def remove_instance(self, instance_id):
        """Remove an instance (cannot remove last instance)."""
        if len(self.root_config["instances"]) <= 1:
            return False  # Must keep at least one instance

        if instance_id in self.root_config["instances"]:
            del self.root_config["instances"][instance_id]
            if instance_id in self.root_config["active_instances"]:
                self.root_config["active_instances"].remove(instance_id)
            self.save()
            return True
        return False

    def set_active_instances(self, instance_ids):
        """Set which instances are active."""
        self.root_config["active_instances"] = instance_ids
        self.save()

    def switch_instance(self, instance_id):
        """Switch to a different instance."""
        if instance_id in self.root_config["instances"]:
            self.instance_id = instance_id
            self.config = self._merge_with_defaults(
                self.root_config["instances"][instance_id],
                DEFAULT_INSTANCE_CONFIG
            )
            return True
        return False

    def _merge_with_defaults(self, loaded_config, defaults):
        """Merge loaded config with defaults to ensure all keys exist."""
        merged = self._deep_copy(defaults)
        for category, values in loaded_config.items():
            if category in merged and isinstance(values, dict):
                merged[category].update(values)
            else:
                merged[category] = values
        return merged

    def _deep_copy(self, obj):
        """Simple deep copy for nested dictionaries (avoids import copy module)."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj

    def export_settings(self, filepath):
        """Export current instance settings to a file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except IOError:
            return False

    def import_settings(self, filepath):
        """Import settings from a file and merge with defaults."""
        try:
            with open(filepath, 'r') as f:
                imported = json.load(f)
            # Validate and merge with defaults to ensure all keys exist
            self.config = self._merge_with_defaults(imported, DEFAULT_INSTANCE_CONFIG)
            return True
        except (IOError, json.JSONDecodeError):
            return False


# Convenience function for quick access
def load_config(config_file=CONFIG_FILE):
    """Load and return a ConfigManager instance."""
    return ConfigManager(config_file)
