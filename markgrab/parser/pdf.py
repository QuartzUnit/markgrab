"""PDF parser — extract text from PDF documents using pdfplumber (MIT)."""

import logging
from io import BytesIO

from markgrab.result import ExtractResult
from markgrab.utils import detect_language

logger = logging.getLogger(__name__)


class PdfParser:
    """Extract text from PDF bytes using pdfplumber."""

    def parse(self, data: bytes, url: str) -> ExtractResult:
        """Parse PDF content.

        Args:
            data: Raw PDF bytes.
            url: Source URL.
        """
        import pdfplumber

        with pdfplumber.open(BytesIO(data)) as pdf:
            meta = pdf.metadata or {}
            title = (meta.get("Title") or meta.get("title") or "").strip()

            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text.strip())

        full_text = "\n\n".join(pages)

        # Build markdown
        md_lines = []
        if title:
            md_lines.append(f"# {title}\n")
        for i, page_text in enumerate(pages, 1):
            if len(pages) > 1:
                md_lines.append(f"## Page {i}\n")
            md_lines.append(page_text)
            md_lines.append("")
        markdown = "\n".join(md_lines).strip()

        language = detect_language(full_text)

        pdf_metadata = {"page_count": len(pages)}
        if meta.get("Author") or meta.get("author"):
            pdf_metadata["author"] = meta.get("Author") or meta["author"]
        if meta.get("Subject") or meta.get("subject"):
            pdf_metadata["subject"] = meta.get("Subject") or meta["subject"]
        if meta.get("CreationDate") or meta.get("creationDate"):
            pdf_metadata["created"] = meta.get("CreationDate") or meta["creationDate"]

        return ExtractResult(
            title=title or "PDF Document",
            text=full_text,
            markdown=markdown,
            word_count=len(full_text.split()),
            language=language,
            content_type="pdf",
            source_url=url,
            metadata=pdf_metadata,
        )
