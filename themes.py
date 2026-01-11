"""
Theme Presets for TimeDateWeather Desktop Widget.
Provides pre-configured color and font combinations for quick styling.
"""

THEMES = {
    "default": {
        "name": "Default",
        "description": "Clean white text with black shadow",
        "colors": {
            "text": "#ffffff",
            "shadow": "#000000",
            "status": "#808080",
            "time_color": "#ffffff",
            "date_color": "#ffffff",
            "weather_color": "#ffffff"
        },
        "fonts": {
            "family": "Segoe UI"
        },
        "appearance": {
            "opacity": 1.0
        }
    },
    "dark_elegant": {
        "name": "Dark Elegant",
        "description": "Muted grays with refined aesthetics",
        "colors": {
            "text": "#e0e0e0",
            "shadow": "#1a1a1a",
            "status": "#666666",
            "time_color": "#ffffff",
            "date_color": "#b0b0b0",
            "weather_color": "#a0a0a0"
        },
        "fonts": {
            "family": "Segoe UI Light"
        },
        "appearance": {
            "opacity": 0.95
        }
    },
    "ocean_blue": {
        "name": "Ocean Blue",
        "description": "Cool blue tones inspired by the sea",
        "colors": {
            "text": "#66ccff",
            "shadow": "#001133",
            "status": "#3399cc",
            "time_color": "#99ddff",
            "date_color": "#66ccff",
            "weather_color": "#33aadd"
        },
        "fonts": {
            "family": "Calibri"
        },
        "appearance": {
            "opacity": 0.9
        }
    },
    "warm_sunset": {
        "name": "Warm Sunset",
        "description": "Warm orange and amber tones",
        "colors": {
            "text": "#ff9966",
            "shadow": "#331100",
            "status": "#cc6633",
            "time_color": "#ffcc99",
            "date_color": "#ff9966",
            "weather_color": "#ff6633"
        },
        "fonts": {
            "family": "Georgia"
        },
        "appearance": {
            "opacity": 0.9
        }
    }
}


def get_theme(theme_id):
    """
    Get a theme by its ID.

    Args:
        theme_id: The theme identifier (e.g., 'default', 'dark_elegant')

    Returns:
        Theme dictionary or default theme if not found
    """
    return THEMES.get(theme_id, THEMES["default"])


def get_theme_names():
    """
    Get list of (id, display_name) tuples for all available themes.

    Returns:
        List of tuples: [(theme_id, theme_name), ...]
    """
    return [(tid, t["name"]) for tid, t in THEMES.items()]


def get_theme_ids():
    """
    Get list of all theme IDs.

    Returns:
        List of theme ID strings
    """
    return list(THEMES.keys())


def apply_theme_to_config(config, theme_id):
    """
    Apply a theme's settings to a config object.
    Only overwrites theme-related settings, preserves others.

    Args:
        config: ConfigManager instance
        theme_id: Theme ID to apply

    Returns:
        True if theme was applied, False if theme not found
    """
    if theme_id not in THEMES:
        return False

    theme = THEMES[theme_id]

    # Apply colors
    if "colors" in theme:
        for key, value in theme["colors"].items():
            config.set("colors", key, value)

    # Apply fonts
    if "fonts" in theme:
        for key, value in theme["fonts"].items():
            config.set("fonts", key, value)

    # Apply appearance
    if "appearance" in theme:
        for key, value in theme["appearance"].items():
            config.set("appearance", key, value)

    # Set the theme identifier
    config.set("appearance", "theme", theme_id)

    return True
