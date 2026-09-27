EXCERPT_MAX_LENGTH = 180
ELLIPSIS = "..."


def truncate_excerpt(text: str, max_length: int = EXCERPT_MAX_LENGTH) -> str:
    if len(text) <= max_length:
        return text
    keep = max(0, max_length - len(ELLIPSIS))
    return text[:keep] + ELLIPSIS
