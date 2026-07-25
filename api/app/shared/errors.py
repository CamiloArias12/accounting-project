class DomainError(Exception):
    """Base of every business error, in any module.

    The web layer maps subclasses to status codes; nothing below it knows that
    HTTP exists.
    """
