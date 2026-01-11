"""
Toast Notification System for TimeDateWeather Desktop Widget.
Provides non-intrusive, animated notifications that fade in and out.
"""

import tkinter as tk


class ToastNotification:
    """
    A toast-style notification that appears near the parent window,
    fades in, displays for a duration, then fades out.
    """

    # Color schemes for different notification types
    COLORS = {
        "info": {"bg": "#333333", "fg": "#ffffff"},
        "success": {"bg": "#2e7d32", "fg": "#ffffff"},
        "warning": {"bg": "#f57c00", "fg": "#ffffff"},
        "error": {"bg": "#c62828", "fg": "#ffffff"}
    }

    def __init__(self, parent, message, duration=3000, notification_type="info"):
        """
        Create and display a toast notification.

        Args:
            parent: Parent tkinter window
            message: Text to display
            duration: How long to show the notification (ms)
            notification_type: One of 'info', 'success', 'warning', 'error'
        """
        self.parent = parent
        self.duration = duration
        self.toast = None

        # Get colors for this notification type
        colors = self.COLORS.get(notification_type, self.COLORS["info"])

        try:
            # Create toast window
            self.toast = tk.Toplevel(parent)
            self.toast.overrideredirect(True)
            self.toast.attributes("-topmost", True)
            self.toast.attributes("-alpha", 0.0)

            # Position near parent widget (bottom-right corner)
            parent.update_idletasks()
            x = parent.winfo_x() + parent.winfo_width() - 200
            y = parent.winfo_y() + parent.winfo_height() + 10
            self.toast.geometry(f"+{x}+{y}")

            # Create rounded-corner effect with frame
            frame = tk.Frame(
                self.toast,
                bg=colors["bg"],
                padx=2,
                pady=2
            )
            frame.pack(fill=tk.BOTH, expand=True)

            # Create label with message
            label = tk.Label(
                frame,
                text=message,
                bg=colors["bg"],
                fg=colors["fg"],
                font=("Segoe UI", 10),
                padx=15,
                pady=10,
                wraplength=250
            )
            label.pack()

            # Start fade-in animation
            self._fade_in()

        except Exception:
            # Silent failure - notifications are non-critical
            if self.toast:
                try:
                    self.toast.destroy()
                except Exception:
                    pass

    def _fade_in(self, alpha=0.0):
        """Animate fade-in effect."""
        try:
            if not self.toast or not self.toast.winfo_exists():
                return

            if alpha < 0.9:
                alpha += 0.1
                self.toast.attributes("-alpha", alpha)
                self.toast.after(30, lambda: self._fade_in(alpha))
            else:
                # Fully visible, wait for duration then fade out
                self.toast.after(self.duration, self._fade_out)
        except Exception:
            pass

    def _fade_out(self, alpha=0.9):
        """Animate fade-out effect."""
        try:
            if not self.toast or not self.toast.winfo_exists():
                return

            if alpha > 0.1:
                alpha -= 0.1
                self.toast.attributes("-alpha", alpha)
                self.toast.after(30, lambda: self._fade_out(alpha))
            else:
                self.toast.destroy()
        except Exception:
            pass

    def destroy(self):
        """Manually destroy the notification."""
        try:
            if self.toast and self.toast.winfo_exists():
                self.toast.destroy()
        except Exception:
            pass


class ToolTip:
    """
    A tooltip that appears when hovering over a widget.
    Provides helpful hints for UI elements.
    """

    def __init__(self, widget, text, delay=500):
        """
        Attach a tooltip to a widget.

        Args:
            widget: The tkinter widget to attach tooltip to
            text: The tooltip text to display
            delay: Delay before showing tooltip (ms)
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip = None
        self.scheduled_id = None

        # Bind mouse events
        widget.bind("<Enter>", self._schedule_show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule_show(self, event=None):
        """Schedule tooltip to appear after delay."""
        self._hide()  # Cancel any existing tooltip
        self.scheduled_id = self.widget.after(self.delay, self._show)

    def _show(self):
        """Display the tooltip."""
        try:
            if self.tooltip:
                return

            # Get widget position
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

            # Create tooltip window
            self.tooltip = tk.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            self.tooltip.attributes("-topmost", True)

            # Create label with tooltip text
            label = tk.Label(
                self.tooltip,
                text=self.text,
                background="#ffffe0",
                foreground="#000000",
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 9),
                padx=6,
                pady=4,
                wraplength=250
            )
            label.pack()
        except Exception:
            pass

    def _hide(self, event=None):
        """Hide and destroy the tooltip."""
        # Cancel scheduled show
        if self.scheduled_id:
            self.widget.after_cancel(self.scheduled_id)
            self.scheduled_id = None

        # Destroy tooltip
        if self.tooltip:
            try:
                self.tooltip.destroy()
            except Exception:
                pass
            self.tooltip = None


def show_toast(parent, message, duration=3000, notification_type="info"):
    """
    Convenience function to show a toast notification.

    Args:
        parent: Parent tkinter window
        message: Text to display
        duration: How long to show the notification (ms)
        notification_type: One of 'info', 'success', 'warning', 'error'

    Returns:
        ToastNotification instance
    """
    return ToastNotification(parent, message, duration, notification_type)
