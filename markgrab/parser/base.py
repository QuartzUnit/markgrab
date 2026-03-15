"""Parser base — content parsing abstraction."""

from abc import ABC, abstractmethod

from markgrab.result import ExtractResult


class Parser(ABC):
    """Abstract base for content parsers."""

    @abstractmethod
    def parse(self, html: str, url: str) -> ExtractResult:
        ...
