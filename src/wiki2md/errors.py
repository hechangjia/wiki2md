class Wiki2MdError(Exception):
    """Base exception for all project-specific failures."""


class InvalidWikipediaUrlError(Wiki2MdError):
    """Raised when a URL is not a supported Wikipedia article URL."""


class UnsupportedPageError(Wiki2MdError):
    """Raised when a URL points to a page type outside the v1 scope."""


class FetchError(Wiki2MdError):
    """Raised when Wikipedia data cannot be fetched successfully."""


class ParseError(Wiki2MdError):
    """Raised when article HTML cannot be normalized safely."""


class WriteError(Wiki2MdError):
    """Raised when output artifacts cannot be written safely."""


class BatchManifestValidationError(Wiki2MdError):
    """Raised when a batch manifest contains invalid rows in strict mode."""

    def __init__(self, invalid_rows: list[object]) -> None:
        super().__init__("Batch manifest validation failed.")
        self.invalid_rows = invalid_rows
