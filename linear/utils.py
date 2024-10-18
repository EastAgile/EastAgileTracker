# linear/utils.py

import asyncio
import os
from functools import wraps

from tqdm import tqdm

PROCESSED_TEAMS_FILE = "linear/processed_teams.txt"


def mark_team_as_processed(team_id):
    """Mark a team as processed by writing its ID to a file."""
    with open(PROCESSED_TEAMS_FILE, "a") as f:
        f.write(f"{team_id}\n")


def get_processed_teams():
    """Get a set of team IDs that have already been processed."""
    if not os.path.exists(PROCESSED_TEAMS_FILE):
        return set()
    with open(PROCESSED_TEAMS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def clear_processed_teams():
    """Clear the list of processed teams."""
    if os.path.exists(PROCESSED_TEAMS_FILE):
        os.remove(PROCESSED_TEAMS_FILE)


def retry_async(max_retries=3, delay=1):
    """
    A decorator for retrying async functions with exponential backoff.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise
                    await asyncio.sleep(delay * (2 ** (retries - 1)))
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def chunk_list(lst, chunk_size):
    """Split a list into smaller chunks of a specified size."""
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def sanitize_name(name, max_length=50):
    """
    Sanitize a name for use in Linear.
    Remove invalid characters and truncate if necessary.
    """
    # Remove or replace invalid characters
    sanitized = "".join(c for c in name if c.isalnum() or c in [" ", "-", "_"])
    # Truncate if longer than max_length
    return sanitized[:max_length].strip()


def map_priority(pt_priority):
    """Map Pivotal Tracker priority to Linear priority."""
    priority_map = {
        "p0": 1,  # Urgent
        "p1": 2,  # High
        "p2": 3,  # Medium
        "p3": 4,  # Low
        "p4": 0,  # No priority
    }
    return priority_map.get(pt_priority.lower(), 0)


def map_state(pt_state):
    """Map Pivotal Tracker state to Linear state."""
    state_map = {
        "unstarted": "Todo",
        "started": "In Progress",
        "finished": "In Review",
        "delivered": "Done",
        "accepted": "Done",
        "rejected": "Todo",
    }
    return state_map.get(pt_state.lower(), "Todo")


def map_issue_type(pt_type):
    """Map Pivotal Tracker issue type to Linear issue type."""
    type_map = {"feature": "Feature", "bug": "Bug", "chore": "Task"}
    return type_map.get(pt_type.lower(), "Feature")


def with_progress(desc=None, total=None):
    """
    Decorator to add a progress bar to a function.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if total is None:
                # If total is None, don't use a progress bar
                return await func(*args, **kwargs)

            pbar = tqdm(total=total, desc=desc, unit="item")
            try:
                result = await func(*args, **kwargs, pbar=pbar)
                pbar.close()
                return result
            except Exception as e:
                pbar.close()
                raise e

        return wrapper

    return decorator
