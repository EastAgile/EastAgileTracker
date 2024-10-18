# config.py

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    # API Configuration
    API_TOKEN = os.getenv("PIVOTAL_TRACKER_API_TOKEN")
    API_BASE_URL = "https://www.pivotaltracker.com/services/v5"

    # Database Configuration
    DB_FILE = os.getenv("DB_FILE", "pivotal_tracker_data.db")

    # File Storage Configuration
    ATTACHMENT_DIR = os.getenv("ATTACHMENT_DIR", "attachments")

    # Ensure the attachment directory exists
    os.makedirs(ATTACHMENT_DIR, exist_ok=True)

    @classmethod
    def get_db_url(cls):
        return f"sqlite:///{cls.DB_FILE}"

    @classmethod
    def get_attachment_path(cls, filename):
        return os.path.join(cls.ATTACHMENT_DIR, filename)

    @classmethod
    def set_api_token(cls, token):
        cls.API_TOKEN = token
        import os

        os.environ["PIVOTAL_TRACKER_API_TOKEN"] = token


# Validate required environment variables
if not Config.API_TOKEN:
    raise ValueError(
        "PIVOTAL_TRACKER_API_TOKEN must be set in the environment or .env file"
    )
