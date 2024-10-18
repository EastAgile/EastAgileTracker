import os

PROCESSED_PROJECTS_FILE = "processed_projects.txt"


def mark_project_as_processed(project_id):
    with open(PROCESSED_PROJECTS_FILE, "a") as f:
        f.write(f"{project_id}\n")


def get_processed_projects():
    if not os.path.exists(PROCESSED_PROJECTS_FILE):
        return set()
    with open(PROCESSED_PROJECTS_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip())


def clear_processed_projects():
    if os.path.exists(PROCESSED_PROJECTS_FILE):
        os.remove(PROCESSED_PROJECTS_FILE)
