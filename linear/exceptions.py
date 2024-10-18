# linear/exceptions.py


class LinearMigrationError(Exception):
    """Base exception for Linear migration errors."""

    pass


class LinearAPIError(LinearMigrationError):
    """Exception raised for errors in the Linear API."""

    def __init__(self, message, errors=None):
        self.message = message
        self.errors = errors
        super().__init__(self.message)


class ConfigurationError(LinearMigrationError):
    """Exception raised for errors in the configuration."""

    pass


class DataMappingError(LinearMigrationError):
    """Exception raised for errors in mapping data from PT to Linear."""

    pass


class AttachmentError(LinearMigrationError):
    """Exception raised for errors in handling attachments."""

    pass


class UserMigrationError(LinearMigrationError):
    """Exception raised for errors in migrating users."""

    pass


class TeamCreationError(LinearMigrationError):
    """Exception raised when creating a Linear team fails."""

    pass


class ProjectCreationError(LinearMigrationError):
    """Exception raised when creating a Linear project fails."""

    pass


class IssueMigrationError(LinearMigrationError):
    """Exception raised for errors in migrating issues."""

    pass


class CycleMigrationError(LinearMigrationError):
    """Exception raised for errors in migrating cycles (iterations)."""

    pass


class CommentMigrationError(LinearMigrationError):
    """Exception raised for errors in migrating comments."""

    pass


class RelationMigrationError(LinearMigrationError):
    """Exception raised for errors in migrating issue relations."""

    pass
