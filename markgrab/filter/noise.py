"""Noise filter — remove ads, navigation, popups from HTML."""

import re

from bs4 import BeautifulSoup

_NOISE_TAGS = frozenset({"script", "style", "noscript", "svg", "iframe"})

_POPUP_SELECTORS = [
    "[class*='cookie']",
    "[class*='consent']",
    "[class*='popup']",
    "[class*='modal']",
    "[id*='cookie']",
    "[id*='consent']",
]


def clean_soup(soup: BeautifulSoup) -> None:
    """Remove noise elements from soup in-place.

    Removes: script/style/noscript/svg/iframe tags,
    cookie/consent/popup/modal elements, hidden elements.
    """
    for tag in soup.find_all(list(_NOISE_TAGS)):
        tag.decompose()

    for selector in _POPUP_SELECTORS:
        for el in soup.select(selector):
            if el.attrs is None:
                continue  # Already decomposed by a prior selector
            el.decompose()

    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        if el.attrs is None:
            continue
        el.decompose()

    for el in soup.find_all(style=re.compile(r"display:\s*none")):
        if el.attrs is None:
            continue
        el.decompose()
