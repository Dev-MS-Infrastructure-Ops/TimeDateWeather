"""
Application Logger for Desktop Widget
Provides simple file-based logging for debugging without disrupting user experience.
"""

import logging
import os
import sys
from datetime import datetime

# Determine log file location
def _get_log_path():
    """Get path for log file in user's app data or script directory."""
    try:
        # Try to use app data folder on Windows
        appdata = os.environ.get('LOCALAPPDATA')
        if appdata:
            log_dir = os.path.join(appdata, 'TimeDateWeather')
            os.makedirs(log_dir, exist_ok=True)
            return os.path.join(log_dir, 'widget.log')
    except Exception:
        pass

    # Fallback to script directory
    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, 'widget.log')
    except Exception:
        return 'widget.log'

# Initialize logger
_logger = None
_log_enabled = True

def _get_logger():
    """Get or create the application logger."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger('TimeDateWeather')
        _logger.setLevel(logging.DEBUG)

        try:
            log_path = _get_log_path()

            # Create file handler with rotation (keep last 100KB)
            handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=100_000,
                backupCount=1,
                encoding='utf-8'
            )
            handler.setLevel(logging.DEBUG)

            # Format: timestamp - level - message
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            _logger.addHandler(handler)
        except Exception:
            # If file logging fails, just use null handler
            _logger.addHandler(logging.NullHandler())

    return _logger

# Import handlers after logger setup
import logging.handlers

def log_error(message, exc_info=None):
    """Log an error message with optional exception info."""
    if not _log_enabled:
        return
    try:
        logger = _get_logger()
        if exc_info:
            logger.error(f"{message}: {exc_info}")
        else:
            logger.error(message)
    except Exception:
        pass  # Logging should never crash the app

def log_warning(message):
    """Log a warning message."""
    if not _log_enabled:
        return
    try:
        _get_logger().warning(message)
    except Exception:
        pass

def log_info(message):
    """Log an info message."""
    if not _log_enabled:
        return
    try:
        _get_logger().info(message)
    except Exception:
        pass

def log_debug(message):
    """Log a debug message."""
    if not _log_enabled:
        return
    try:
        _get_logger().debug(message)
    except Exception:
        pass

def log_exception(context=""):
    """Log the current exception with traceback."""
    if not _log_enabled:
        return
    try:
        import traceback
        tb = traceback.format_exc()
        _get_logger().error(f"{context}\n{tb}" if context else tb)
    except Exception:
        pass

def disable_logging():
    """Disable all logging (for performance if needed)."""
    global _log_enabled
    _log_enabled = False

def enable_logging():
    """Re-enable logging."""
    global _log_enabled
    _log_enabled = True

def get_log_path():
    """Return the path to the log file (for display in UI if needed)."""
    return _get_log_path()
