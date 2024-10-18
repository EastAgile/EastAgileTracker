class JiraMigrationError(Exception):
    """Base exception for Jira migration errors."""

    pass


class JiraAPIError(JiraMigrationError):
    """Exception raised for errors in the Jira API."""

    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class RateLimitError(JiraAPIError):
    """Exception raised when Jira API rate limit is exceeded."""

    pass


class ConfigurationError(JiraMigrationError):
    """Exception raised for errors in the configuration."""

    pass


class DataMappingError(JiraMigrationError):
    """Exception raised for errors in mapping data from PT to Jira."""

    pass


class AttachmentError(JiraMigrationError):
    """Exception raised for errors in handling attachments."""

    pass


class UserMigrationError(JiraMigrationError):
    """Exception raised for errors in migrating users."""

    pass


class ProjectCreationError(JiraAPIError):
    """Exception raised when creating a Jira project fails."""

    pass


class IssueMigrationError(JiraMigrationError):
    """Exception raised for errors in migrating issues (stories/epics/tasks)."""

    pass


class DatabaseError(JiraMigrationError):
    """Exception raised for errors in database operations."""

    pass


class CommentMigrationError(JiraMigrationError):
    """Exception raised for errors in migrating comments."""

    pass


class SprintMigrationError(JiraMigrationError):
    """Exception raised for errors in migrating sprints."""

    pass
