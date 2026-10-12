"""First real Anthropic API call: answer, tokens, latency and cost.

Compares the Day 1 chars/4 token estimate with the real input-token count
returned by the API. Use --no-system to send the question without the
system prompt.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from day01.token_estimator import estimate_tokens  # noqa: E402

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 300
# USD per million tokens for Claude Haiku 4.5. Verify against current pricing.
INPUT_PRICE_PER_MTOK = 1.00
OUTPUT_PRICE_PER_MTOK = 5.00

SYSTEM_PROMPT = (
    "You are a Change Management assistant for a telecom IT team. "
    "Answer in 2–3 sentences."
)
QUESTION = "What's the lead time for a normal change?"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-system",
        action="store_true",
        help="send the question without the system prompt",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "Error: ANTHROPIC_API_KEY is not set. Add a line "
            "ANTHROPIC_API_KEY=<your key> to the .env file in the "
            "ai-builder-portfolio folder."
        )

    client = anthropic.Anthropic(api_key=api_key)
    kwargs = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": QUESTION}],
    }
    if not args.no_system:
        kwargs["system"] = SYSTEM_PROMPT

    start = time.perf_counter()
    try:
        response = client.messages.create(**kwargs)
    except anthropic.AuthenticationError:
        sys.exit("Error: the API rejected ANTHROPIC_API_KEY. Check the key in .env.")
    except anthropic.APIError as e:
        sys.exit(f"Error: API call failed ({type(e).__name__}): {e.message}")
    latency_ms = (time.perf_counter() - start) * 1000

    answer = "".join(b.text for b in response.content if b.type == "text")
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (
        input_tokens / 1_000_000 * INPUT_PRICE_PER_MTOK
        + output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MTOK
    )

    print(f"Model:   {MODEL} ({'no system prompt' if args.no_system else 'with system prompt'})")
    print(f"Question: {QUESTION}\n")
    print(f"Answer:\n{answer}\n")
    print(f"Input tokens:  {input_tokens}")
    print(f"Output tokens: {output_tokens}")
    print(f"Latency:       {latency_ms:.0f} ms")
    print(f"Cost:          ${cost:.6f}")
    counted = "question + framing" if args.no_system else "question + system prompt + framing"
    print(
        f"\nDay 1 estimate (chars/4, question only): ~{estimate_tokens(QUESTION)} tokens"
        f" | real input tokens ({counted}): {input_tokens}"
    )


if __name__ == "__main__":
    main()
