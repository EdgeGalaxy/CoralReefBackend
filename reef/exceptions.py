class ModelException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)


class ObjectNotFoundError(ModelException):
    """Raised when an object is not found."""
    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message, status_code)


class AssociatedObjectExistsError(ModelException):
    """Raised when an object has associated objects."""
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message, status_code)



class InvalidStateError(ModelException):
    """Raised when an object is in an invalid state."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code)


class AuthenticationError(Exception):
    """认证错误"""
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message, status_code)


class ValidationError(Exception):
    """验证错误"""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code)
