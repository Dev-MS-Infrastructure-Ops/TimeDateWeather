"""
Theme Presets for TimeDateWeather Desktop Widget.
Provides pre-configured color and font combinations for quick styling.
"""

THEMES = {
    "default": {
        "name": "Studio Glass",
        "description": "Warm white with cool weather accents",
        "colors": {
            "text": "#f5f2ea",
            "shadow": "#121212",
            "status": "#8a8a8a",
            "time_color": "#fefcf7",
            "date_color": "#d8d2c6",
            "weather_color": "#c7d3e8"
        },
        "fonts": {
            "family": "Bahnschrift"
        },
        "appearance": {
            "opacity": 1.0
        }
    },
    "noir_mint": {
        "name": "Noir Mint",
        "description": "Deep blacks with mint highlights",
        "colors": {
            "text": "#dffcf2",
            "shadow": "#081715",
            "status": "#5da79a",
            "time_color": "#b8fff0",
            "date_color": "#8ad6c5",
            "weather_color": "#e7fff8"
        },
        "fonts": {
            "family": "Cascadia Code"
        },
        "appearance": {
            "opacity": 0.96
        }
    },
    "cobalt_dawn": {
        "name": "Cobalt Dawn",
        "description": "Cool blues with crisp contrast",
        "colors": {
            "text": "#d9e8ff",
            "shadow": "#0a1020",
            "status": "#5e7bb3",
            "time_color": "#ffffff",
            "date_color": "#b6c9f0",
            "weather_color": "#8ab4ff"
        },
        "fonts": {
            "family": "Yu Gothic UI Semibold"
        },
        "appearance": {
            "opacity": 0.95
        }
    },
    "sunset_signal": {
        "name": "Sunset Signal",
        "description": "Warm amber with strong readability",
        "colors": {
            "text": "#ffd2a6",
            "shadow": "#2a0f05",
            "status": "#c18a5a",
            "time_color": "#ffe0bf",
            "date_color": "#f5b77f",
            "weather_color": "#ff9b5f"
        },
        "fonts": {
            "family": "Trebuchet MS"
        },
        "appearance": {
            "opacity": 0.95
        }
    },
    "paper_ink": {
        "name": "Paper Ink",
        "description": "Soft paper with crisp ink",
        "colors": {
            "text": "#1f1b16",
            "shadow": "#e3ddcf",
            "status": "#7b6e61",
            "time_color": "#14110d",
            "date_color": "#2d2620",
            "weather_color": "#3b322a"
        },
        "fonts": {
            "family": "Georgia"
        },
        "appearance": {
            "opacity": 0.92
        }
    },
    "glacier": {
        "name": "Glacier",
        "description": "Cold light with steel shadow",
        "colors": {
            "text": "#eaf7ff",
            "shadow": "#0b1a22",
            "status": "#5c91a5",
            "time_color": "#f8fdff",
            "date_color": "#cfe9f5",
            "weather_color": "#9ad4e6"
        },
        "fonts": {
            "family": "Calibri Light"
        },
        "appearance": {
            "opacity": 0.93
        }
    }
}


def get_theme(theme_id):
    """
    Get a theme by its ID.

    Args:
        theme_id: The theme identifier (e.g., 'default', 'noir_mint')

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
