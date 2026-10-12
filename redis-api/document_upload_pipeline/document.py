from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Document:
    """A PDF's extracted text, plus its embedding once generated."""

    filename: str
    filepath: str
    content: str
    # repr=False keeps print() readable; 512 floats would flood the output
    embedding: list[float] | None = field(default=None, repr=False)


@dataclass
class SearchResult:
    """A document returned by vector search, with its cosine similarity (0-1, higher = closer)."""

    filename: str
    content: str
    uploaded_at: datetime
    similarity: float
