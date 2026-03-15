"""Content parsers."""

from markgrab.parser.base import Parser
from markgrab.parser.docx import DocxParser
from markgrab.parser.html import HtmlParser
from markgrab.parser.pdf import PdfParser
from markgrab.parser.youtube import YouTubeParser

__all__ = ["Parser", "HtmlParser", "YouTubeParser", "PdfParser", "DocxParser"]
