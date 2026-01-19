from enum import Enum, auto


class FormatType(Enum):
    """Supported book format types."""

    MDBOOK = auto()
    GITBOOK = auto()
    LEANPUB = auto()
    BOOKDOWN = auto()
    AUTO = auto()
