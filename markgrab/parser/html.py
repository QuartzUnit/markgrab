"""HTML parser — extract content from HTML using BeautifulSoup + markdownify."""

import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter

from markgrab.filter.density import filter_low_density
from markgrab.filter.noise import clean_soup
from markgrab.parser.base import Parser
from markgrab.result import ExtractResult
from markgrab.utils import detect_language

logger = logging.getLogger(__name__)

_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_MULTI_SPACE_RE = re.compile(r" {2,}")


class _BrFixedConverter(MarkdownConverter):
    """Workaround for markdownify #244 / #58: <br> text loss.

    Python's html.parser treats mixed <br> and <br /> as an opening tag,
    swallowing subsequent text as children.  The upstream convert_br()
    discards the ``text`` parameter, so any swallowed content is lost.
    This override preserves it.
    """

    def convert_br(self, el, text, parent_tags):
        if '_inline' in parent_tags:
            return ' ' + text if text else ' '
        if self.options['newline_style'].lower() == 'backslash':
            newline = '\\\n'
        else:
            newline = '  \n'
        return newline + text if text else newline


def _md_convert(html: str, **kwargs) -> str:
    return _BrFixedConverter(**kwargs).convert(html)


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

    # CSS selectors for content detection — ordered specific → generic.
    # Tried when semantic elements are missing or wrap the entire page.
    _CONTENT_SELECTORS = (
        # ID-based (most specific)
        "#contentBody", "#powerbbsContent", "#article-body",
        "#mArticle", "#postContent", "#post-content",
        # Class-based (common patterns)
        ".view-content", ".post-content", ".article-content",
        ".content-wrap", ".entry-content", ".article-body",
        ".post-body", ".board-content", ".detail-content",
        ".story-body", ".article__body", ".post__content",
    )

    def _find_content(self, soup: BeautifulSoup) -> Tag | BeautifulSoup:
        """Find main content area with prioritized detection.

        Priority: semantic element (if focused) > CSS class/id > semantic element (broad) > body.
        """
        # 1. Try semantic elements
        semantic_hit = None
        for selector in ("article", "main", "[role='main']"):
            found = soup.select_one(selector)
            if found and len(found.get_text(strip=True)) > 100:
                # Check for a more specific content area inside
                inner = self._find_content_by_class(found)
                if inner:
                    return inner
                semantic_hit = found
                break

        # 2. Try CSS class/id selectors on full page
        by_class = self._find_content_by_class(soup)
        if by_class:
            return by_class

        # 3. Return the semantic hit if we had one (even if broad)
        if semantic_hit is not None:
            return semantic_hit

        # 4. Body fallback — remove page-level noise
        body = soup.find("body") or soup
        for tag in body.find_all(["nav", "aside"], recursive=False):
            tag.decompose()
        for tag in body.find_all("footer", recursive=False):
            tag.decompose()

        return body

    def _find_content_by_class(self, root: Tag | BeautifulSoup) -> Tag | None:
        """Find content area using common CSS class/id selectors."""
        for sel in self._CONTENT_SELECTORS:
            el = root.select_one(sel)
            if el and len(el.get_text(strip=True)) > 100:
                return el
        return None

    def _to_markdown(self, content: Tag | BeautifulSoup) -> str:
        md = _md_convert(str(content), heading_style="ATX", bullets="-")
        return _MULTI_NEWLINE_RE.sub("\n\n", md).strip()

    def _to_text(self, content: Tag | BeautifulSoup) -> str:
        text = content.get_text(separator="\n", strip=True)
        text = _MULTI_NEWLINE_RE.sub("\n\n", text)
        return _MULTI_SPACE_RE.sub(" ", text).strip()

