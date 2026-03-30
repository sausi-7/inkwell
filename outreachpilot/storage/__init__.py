"""Local file storage layer for signals, campaigns, and progress."""

from outreachpilot.storage.progress import load_progress, save_progress
from outreachpilot.storage.signals import save_signals, load_signals, load_recent_signal_ids

__all__ = ["load_progress", "save_progress", "save_signals", "load_signals", "load_recent_signal_ids"]
