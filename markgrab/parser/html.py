"""HTML parser — extract content from HTML using BeautifulSoup + markdownify."""

import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md_convert

from markgrab.filter.density import filter_low_density
from markgrab.filter.noise import clean_soup
from markgrab.parser.base import Parser
from markgrab.result import ExtractResult
from markgrab.utils import detect_language

logger = logging.getLogger(__name__)

_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_MULTI_SPACE_RE = re.compile(r" {2,}")


class HtmlParser(Parser):
    """Parse HTML into ExtractResult using BeautifulSoup + markdownify."""

    def parse(self, html: str, url: str) -> ExtractResult:
        soup = BeautifulSoup(html, "html.parser")

        # Extract title and metadata before noise removal
        title = self._extract_title(soup)
        metadata = self._extract_metadata(soup, url)

        # Remove noise elements
        clean_soup(soup)

        # Find main content area
        content = self._find_content(soup)

        # Remove low-density sidebars/navigation from content
        filter_low_density(content)

        # Convert
        markdown = self._to_markdown(content)
        text = self._to_text(content)
        language = detect_language(text)

        return ExtractResult(
            title=title,
            text=text,
            markdown=markdown,
            word_count=len(text.split()),
            language=language,
            content_type="article",
            source_url=url,
            metadata=metadata,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        # Priority: og:title > <title> > first <h1>
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            return og["content"].strip()

        tag = soup.find("title")
        if tag and tag.string:
            return tag.string.strip()

        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return ""

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> dict:
        meta: dict = {"url": url, "domain": urlparse(url).netloc}

        for prop, key in [
            ("og:description", "description"),
            ("og:image", "image"),
        ]:
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content"):
                meta[key] = tag["content"].strip()

        author = soup.find("meta", attrs={"name": "author"})
        if author and author.get("content"):
            meta["author"] = author["content"].strip()

        for attr in ("article:published_time", "datePublished", "date"):
            tag = soup.find("meta", property=attr) or soup.find("meta", attrs={"name": attr})
            if tag and tag.get("content"):
                meta["published"] = tag["content"].strip()
                break

        return meta

    def _find_content(self, soup: BeautifulSoup) -> Tag | BeautifulSoup:
        """Find main content area: article > main > [role=main] > body."""
        for selector in ("article", "main", "[role='main']"):
            found = soup.select_one(selector)
            if found and len(found.get_text(strip=True)) > 100:
                return found

        # Body fallback — remove page-level noise
        body = soup.find("body") or soup
        for tag in body.find_all(["nav", "aside"], recursive=False):
            tag.decompose()
        for tag in body.find_all("footer", recursive=False):
            tag.decompose()

        return body

    def _to_markdown(self, content: Tag | BeautifulSoup) -> str:
        md = md_convert(str(content), heading_style="ATX", bullets="-")
        return _MULTI_NEWLINE_RE.sub("\n\n", md).strip()

    def _to_text(self, content: Tag | BeautifulSoup) -> str:
        text = content.get_text(separator="\n", strip=True)
        text = _MULTI_NEWLINE_RE.sub("\n\n", text)
        return _MULTI_SPACE_RE.sub(" ", text).strip()

