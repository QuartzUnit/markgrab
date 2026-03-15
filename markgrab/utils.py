"""Shared utilities."""

import re

_KOREAN_RE = re.compile(r"[\uac00-\ud7a3]")
_JAPANESE_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


def detect_language(text: str) -> str:
    """Detect language from text using character frequency analysis."""
    sample = text[:2000]
    if not sample:
        return "en"

    total = len(sample)
    ko = len(_KOREAN_RE.findall(sample))
    ja = len(_JAPANESE_RE.findall(sample))
    zh = len(_CHINESE_RE.findall(sample))

    if ko > 50 or (total and ko / total > 0.1):
        return "ko"
    if ja > 50 or (total and ja / total > 0.1):
        return "ja"
    if zh > 50 or (total and zh / total > 0.1):
        return "zh"

    return "en"
