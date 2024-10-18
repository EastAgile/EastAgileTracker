# exceptions.py


class APIError(Exception):
    """Exception raised for errors in the API."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class ConfigurationError(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class DatabaseError(Exception):
    """Exception raised for errors in database operations."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class ETLError(Exception):
    """Exception raised for errors during the ETL process."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
