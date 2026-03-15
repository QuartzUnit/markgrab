"""Truncate filter — limit content length."""

from markgrab.result import ExtractResult


def truncate_result(result: ExtractResult, *, max_chars: int = 50_000) -> ExtractResult:
    """Truncate text and markdown fields to max_chars.

    Tries to break at the last newline before the limit.
    Returns the original result if no truncation needed.
    """
    if max_chars <= 0 or (len(result.text) <= max_chars and len(result.markdown) <= max_chars):
        return result

    text = result.text
    markdown = result.markdown

    if len(text) > max_chars:
        text = text[:max_chars].rsplit("\n", 1)[0] + "\n\n[truncated]"

    if len(markdown) > max_chars:
        markdown = markdown[:max_chars].rsplit("\n", 1)[0] + "\n\n[truncated]"

    return ExtractResult(
        title=result.title,
        text=text,
        markdown=markdown,
        word_count=len(text.split()),
        language=result.language,
        content_type=result.content_type,
        source_url=result.source_url,
        metadata=result.metadata,
    )
