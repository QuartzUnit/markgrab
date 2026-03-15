"""Extract result data class."""

from dataclasses import dataclass, field


@dataclass
class ExtractResult:
    """Result of content extraction from a URL."""

    title: str
    text: str
    markdown: str
    word_count: int
    language: str
    content_type: str
    source_url: str
    metadata: dict = field(default_factory=dict)
