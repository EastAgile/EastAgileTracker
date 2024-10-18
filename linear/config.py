# linear/config.py

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    # Linear API Configuration
    LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
    LINEAR_API_URL = "https://api.linear.app/graphql"

    # User mapping, pt user id -> linear user object
    LINEAR_USER_MAP = {}  # Will be populated during migration

    # Workflow state mapping (PT state -> Linear state)
    WORKFLOW_STATE_MAP = {
        "unstarted": "Todo",
        "started": "In Progress",
        "finished": "In Review",
        "delivered": "Done",
        "accepted": "Done",
        "rejected": "Todo",
    }

    # Issue type mapping (PT type -> Linear type)
    ISSUE_TYPE_MAP = {"feature": "Feature", "bug": "Bug", "chore": "Task"}

    # Priority mapping (PT -> Linear)
    PRIORITY_MAP = {
        "p0": 1,  # Urgent
        "p1": 2,  # High
        "p2": 3,  # Medium
        "p3": 4,  # Low
        "p4": 0,  # No priority
    }

    # Base directory for attachments (shared with PT and JIRA code)
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ATTACHMENT_DIR = os.path.join(BASE_DIR, "attachments")

    # Maximum number of concurrent API requests
    MAX_CONCURRENT_REQUESTS = 5

    # Batch size for bulk operations
    BATCH_SIZE = 50

    @classmethod
    def validate(cls):
        if not cls.LINEAR_API_KEY:
            raise ValueError(
                "LINEAR_API_KEY must be set in the environment or .env file"
            )

    @classmethod
    def get_attachment_path(cls, project_id, story_id, filename):
        return os.path.join(
            cls.ATTACHMENT_DIR, str(project_id), str(story_id), filename
        )


# Validate configuration on import
Config.validate()
