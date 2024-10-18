# jira/utils.py

import os
from functools import wraps

from tqdm import tqdm


def progress_bar(iterable=None, desc=None, total=None, **kwargs):
    """
    Create a progress bar for an iterable or manual updates.

    :param iterable: Iterable to wrap with progress bar
    :param desc: Description for the progress bar
    :param total: Total number of items (required if iterable is None)
    :param kwargs: Additional keyword arguments for tqdm
    :return: tqdm instance
    """
    return tqdm(
        iterable=iterable,
        desc=desc,
        total=total,
        ncols=100,
        unit="item",
        unit_scale=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        **kwargs,
    )


def with_progress(desc=None, total=None):
    """
    Decorator to add a progress bar to a function.

    :param desc: Description for the progress bar
    :param total: Total number of items (required for manual updates)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            pbar = progress_bar(desc=desc, total=total)
            try:
                result = await func(*args, **kwargs, pbar=pbar)
                pbar.close()
                return result
            except Exception as e:
                pbar.close()
                raise e

        return wrapper

    return decorator


IMPORTED_PROJECTS_FILE = "jira/imported_projects.txt"


def mark_project_as_imported(project_id):
    with open(IMPORTED_PROJECTS_FILE, "a") as f:
        f.write(f"{project_id}\n")


def get_imported_projects():
    if not os.path.exists(IMPORTED_PROJECTS_FILE):
        return set()
    with open(IMPORTED_PROJECTS_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip())


def clear_imported_projects():
    if os.path.exists(IMPORTED_PROJECTS_FILE):
        os.remove(IMPORTED_PROJECTS_FILE)
