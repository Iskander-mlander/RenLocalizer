"""
Custom exceptions for RenLocalizer.
"""

class RenLocalizerError(Exception):
    """Base exception for RenLocalizer."""
    pass

class ProxyError(RenLocalizerError):
    """Raised when proxy-related errors occur."""
    pass

class TranslationError(RenLocalizerError):
    """Raised when translation-related errors occur."""
    pass

class ParseError(RenLocalizerError):
    """Raised when parsing-related errors occur."""
    pass

class ConfigError(RenLocalizerError):
    """Raised when configuration-related errors occur."""
    pass

class GuiError(RenLocalizerError):
    """Raised when GUI-related errors occur."""
    pass
