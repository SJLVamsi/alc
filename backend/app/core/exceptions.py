class ALCException(Exception):
    pass


class BrowserError(ALCException):
    pass


class NavigationError(ALCException):
    pass


class LLMError(ALCException):
    pass


class DatabaseError(ALCException):
    pass


class AutomationError(ALCException):
    pass
