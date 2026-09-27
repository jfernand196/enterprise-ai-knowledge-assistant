CHARS_PER_TOKEN = 4
TOKENS_PER_MILLION = 1_000_000
COST_PRECISION = 6


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_cost_usd(input_tokens: int, output_tokens: int, input_rate: float, output_rate: float) -> float:
    return round(
        (input_tokens / TOKENS_PER_MILLION) * input_rate
        + (output_tokens / TOKENS_PER_MILLION) * output_rate,
        COST_PRECISION,
    )
