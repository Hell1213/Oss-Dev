import tiktoken


def get_tokenizer(model: str):
    """Get a tokenization function for a model.

    Args:
        model: Model name used to select a tiktoken encoding.

    Returns:
        A callable that encodes text into token IDs. Falls back to the
        ``cl100k_base`` encoding when the model-specific encoding is unavailable.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return encoding.encode
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
        return encoding.encode


def count_tokens(text: str, model: str = "gemini-2.0-flash-exp") -> int:
    """Count the number of tokens in text for a model.

    Args:
        text: Text to count tokens for.
        model: Model name used to select a tokenizer.

    Returns:
        Number of tokens in ``text``.
    """
    tokenizer = get_tokenizer(model)

    if tokenizer:
        return len(tokenizer(text))

    return estimate_tokens(text)


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in text using character count.

    Args:
        text: Text to estimate token count for.

    Returns:
        Estimated token count, with a minimum of 1.
    """
    return max(1, len(text) // 4)


def truncate_text(
    text: str,
    model: str,
    max_tokens: int,
    suffix: str = "\n... [truncated]",
    preserve_lines: bool = True,
):
    """Truncate text to fit within a maximum token count.

    Args:
        text: Text to truncate.
        model: Model name used to count tokens.
        max_tokens: Maximum number of tokens allowed in the returned text.
        suffix: Text appended when truncation occurs.
        preserve_lines: Whether to truncate only at line boundaries when possible.

    Returns:
        The original text when it fits within ``max_tokens``; otherwise, a
        truncated version with ``suffix`` appended.
    """
    current_tokens = count_tokens(text, model)
    if current_tokens <= max_tokens:
        return text

    suffix_tokens = count_tokens(suffix, model)
    target_tokens = max_tokens - suffix_tokens

    if target_tokens <= 0:
        return suffix.strip()

    if preserve_lines:
        return _truncate_by_lines(text, target_tokens, suffix, model)
    else:
        return _truncate_by_chars(text, target_tokens, suffix, model)


def _truncate_by_lines(text: str, target_tokens: int, suffix: str, model: str) -> str:
    lines = text.split("\n")
    result_lines: list[str] = []
    current_tokens = 0

    for line in lines:
        line_tokens = count_tokens(line + "\n", model)
        if current_tokens + line_tokens > target_tokens:
            break
        result_lines.append(line)
        current_tokens += line_tokens

    if not result_lines:
        # Fall back to character truncation if no complete lines fit
        return _truncate_by_chars(text, target_tokens, suffix, model)

    return "\n".join(result_lines) + suffix


def _truncate_by_chars(text: str, target_tokens: int, suffix: str, model: str) -> str:
    # Binary search for the right length
    low, high = 0, len(text)

    while low < high:
        mid = (low + high + 1) // 2
        if count_tokens(text[:mid], model) <= target_tokens:
            low = mid
        else:
            high = mid - 1

    return text[:low] + suffix
