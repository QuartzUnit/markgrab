"""Content density filter — remove sidebars and navigation from content area."""

import logging

from bs4 import Tag

logger = logging.getLogger(__name__)

# Block-level elements to analyze for link density
_BLOCK_TAGS = frozenset({"div", "section", "ul", "ol", "table", "form", "dl"})

# Class/id patterns that indicate sidebar/non-content blocks
_SIDEBAR_PATTERNS = (
    "sidebar",
    "related",
    "widget",
    "toc",
    "breadcrumb",
    "social",
    "share",
    "comment",
    "advert",
    "promo",
    "recommend",
    "popular",
    "trending",
    "signup",
    "newsletter",
    "subscribe",
)

# Link density above this = likely navigation, not content
_LINK_DENSITY_THRESHOLD = 0.5

# Minimum text length to consider for link density analysis
_MIN_BLOCK_TEXT = 25


def filter_low_density(content: Tag) -> None:
    """Remove low-density sidebar/navigation blocks from content area in-place.

    Three-pass approach:
    1. Remove <aside>/<nav> tags (semantically non-content)
    2. Remove elements matching sidebar class/id patterns
    3. Remove direct block children with high link density
    """
    # Pass 1: semantic non-content tags inside content
    for tag in content.find_all(["aside", "nav"]):
        logger.debug("Removing <%s> from content", tag.name)
        tag.decompose()

    # Pass 2: sidebar/widget pattern matching
    for pattern in _SIDEBAR_PATTERNS:
        for selector in (f"[class*='{pattern}']", f"[id*='{pattern}']"):
            for el in content.select(selector):
                if el.attrs is None:
                    continue  # Already decomposed by a prior pattern
                logger.debug("Removing sidebar pattern '%s': %s", pattern, el.get("class") or el.get("id"))
                el.decompose()

    # Pass 3: link density on direct block children
    for child in list(content.children):
        if not isinstance(child, Tag):
            continue
        if child.name not in _BLOCK_TAGS:
            continue

        text = child.get_text(strip=True)
        if not text or len(text) < _MIN_BLOCK_TEXT:
            continue

        links_text = "".join(a.get_text(strip=True) for a in child.find_all("a"))
        if not links_text:
            continue

        link_ratio = len(links_text) / len(text)
        if link_ratio > _LINK_DENSITY_THRESHOLD:
            logger.debug("Removing high link-density block (%.0f%%): <%s>", link_ratio * 100, child.name)
            child.decompose()
