"""Rough token and cost estimator for sample change-request questions.

Rule of thumb: one token is about 4 characters of English text, so
tokens ~= characters / 4. This is only an estimate. Real tokenizers split
text differently, so the token count the API returns is the source of truth.
"""

import math

CHARS_PER_TOKEN = 4
# USD per million input tokens for Claude Haiku 4.5. Verify against current pricing.
HAIKU_INPUT_PRICE_PER_MTOK = 1.00

QUESTIONS = [
    "What's the lead time for a normal change?",
    "Who approves an emergency change?",
    "How do I raise a standard change request?",
    "What is the CAB meeting schedule?",
    "Can a change be scheduled during a freeze window?",
    "What information is required in a rollback plan?",
    "How do I cancel an approved change request?",
    "How do I describe the business reason for a change?",
]


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def main() -> None:
    total_chars = 0
    total_tokens = 0
    print(f"{'#':>2} {'chars':>5} {'~tokens':>7}  question")
    for i, question in enumerate(QUESTIONS, start=1):
        chars = len(question)
        tokens = estimate_tokens(question)
        total_chars += chars
        total_tokens += tokens
        print(f"{i:>2} {chars:>5} {tokens:>7}  {question}")

    cost = total_tokens / 1_000_000 * HAIKU_INPUT_PRICE_PER_MTOK
    print(f"\nTotal: {total_chars} chars, ~{total_tokens} tokens")
    print(f"Estimated Haiku input cost: ${cost:.6f} "
          f"(at ${HAIKU_INPUT_PRICE_PER_MTOK:.2f} per million tokens)")


if __name__ == "__main__":
    main()
