"""Controlled errors for CPHD inspection. The CLI maps these to exit code 2."""


class CphdError(Exception):
    """Base class: the file cannot be inspected; the message says why."""


class UnsupportedFormatError(CphdError):
    """Recognizable but not supported (for example an unsupported CPHD version)."""


class MalformedFileError(CphdError):
    """Missing, empty, truncated or internally inconsistent file."""
