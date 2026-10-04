"""Token estimation module.

Provides documented, model-agnostic token approximations.
Note: These numbers are estimates based on standard byte-pair encoding (BPE)
heuristics (~4 characters per token across common LLM tokenizers such as
cl100k_base, llama, and claude tokenizers). They should always be presented as
'Estimated tokens' rather than exact counts.
"""

from __future__ import annotations

# Standard heuristic for English and source code across modern BPE tokenizers
DEFAULT_CHARS_PER_TOKEN: float = 4.0


def estimate_tokens(text: str, chars_per_token: float = DEFAULT_CHARS_PER_TOKEN) -> int:
    """Estimate token count for a given text string.

    Args:
        text: The source text content.
        chars_per_token: Average characters per token (default: 4.0).

    Returns:
        Estimated token count as an integer.
    """
    if not text:
        return 0
    if chars_per_token <= 0:
        chars_per_token = DEFAULT_CHARS_PER_TOKEN

    return max(1, round(len(text) / chars_per_token))


def estimate_tokens_from_char_count(
    char_count: int, chars_per_token: float = DEFAULT_CHARS_PER_TOKEN
) -> int:
    """Estimate token count directly from character count.

    Args:
        char_count: Total characters in the file.
        chars_per_token: Average characters per token (default: 4.0).

    Returns:
        Estimated token count as an integer.
    """
    if char_count <= 0:
        return 0
    if chars_per_token <= 0:
        chars_per_token = DEFAULT_CHARS_PER_TOKEN

    return max(1, round(char_count / chars_per_token))
