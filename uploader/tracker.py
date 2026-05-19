"""
platform/tracker.py — Duplicate post tracker
Reads/writes posted.json to avoid re-posting the same content.
Reusable across any bot project — no changes needed.

Usage:
  from platform.tracker import load_posted, is_posted, mark_posted, save_posted

  posted = load_posted()
  if not is_posted(item_id, posted):
      # ... generate and post ...
      posted = mark_posted(item_id, posted)
      save_posted(posted)
"""

import json
import os

_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKER_FILE = os.path.join(_ROOT, "posted.json")


def load_posted() -> list:
    """Load the list of already-posted IDs. Returns [] if file doesn't exist."""
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posted(posted: list):
    """Write the posted list back to disk."""
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(posted, f, indent=2, ensure_ascii=False)


def is_posted(item_id: str, posted: list) -> bool:
    """Check if item_id has already been posted."""
    return item_id in posted


def mark_posted(item_id: str, posted: list) -> list:
    """Add item_id to the posted list. Keeps only last 1000 entries."""
    posted.append(item_id)
    return posted[-1000:]
