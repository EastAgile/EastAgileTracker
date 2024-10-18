# config.py

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    # Jira API Configuration
    JIRA_URL = os.getenv("JIRA_URL")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    JIRA_ACCOUNT_ID = os.getenv("JIRA_ACCOUNT_ID")

    # Story Points Field ID
    JIRA_STORY_POINTS_FIELD = os.getenv("JIRA_STORY_POINTS_FIELD", "customfield_10036")
    JIRA_EPIC_NAME_FIELD = os.getenv("JIRA_EPIC_NAME_FIELD", "customfield_10011")
    JIRA_ISSUE_TYPE_SCHEME = os.getenv("JIRA_ISSUE_TYPE_SCHEME", "10000")

    JIRA_CUSTOM_FIELDS = [
        JIRA_STORY_POINTS_FIELD,
        "assignee",
        "labels",
    ]

    # Migration Settings
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    RATE_LIMIT_PAUSE = float(os.getenv("RATE_LIMIT_PAUSE", 1.0))

    # Global Workflow Scheme ID (will be set during migration)
    GLOBAL_WORKFLOW_NAME = "PT Migration Global Workflow"
    GLOBAL_WORKFLOW_SCHEME_ID = 10004
    GLOBAL_WORKFLOW_ID = None

    JIRA_PRIORITY_MAP = {
        "p0": "1",
        "p1": "1",
        "p2": "2",
        "p3": "3",
        "p4": "4",
    }

    @classmethod
    def validate(cls):
        required_vars = [
            "JIRA_URL",
            "JIRA_EMAIL",
            "JIRA_API_TOKEN",
            "JIRA_STORY_POINTS_FIELD",
        ]
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    @classmethod
    def set_global_workflow_scheme_id(cls, scheme_id):
        print(f"Setting GLOBAL_WORKFLOW_SCHEME_ID: {scheme_id}")
        cls.GLOBAL_WORKFLOW_SCHEME_ID = scheme_id

    @classmethod
    def set_global_workflow_id(cls, workflow_id):
        cls.GLOBAL_WORKFLOW_ID = workflow_id


# Validate configuration on import
Config.validate()
