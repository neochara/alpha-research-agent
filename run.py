from __future__ import annotations

import argparse
from dotenv import load_dotenv

from agent import run_research
from data import download_prices
from research_store import reset_store

DEFAULT_QUESTION = """
Find a simple, robust cross-sectional momentum signal in the available sector ETF
universe. Start from a conventional medium-horizon momentum idea, investigate a small
number of interpretable variants, account for transaction costs, and do not inspect the
held-out test period.
""".strip()


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run the Alpha Research Agent.")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument(
        "--model",
        default=None,
        help="Optional OpenAI model override. Otherwise use AGENT_MODEL or SDK default.",
    )
    args = parser.parse_args()

    if args.reset:
        reset_store()

    download_prices(force=args.refresh_data)
    memo, memo_path = run_research(args.question, model=args.model)
    print(memo)
    print(f"\nSaved memo: {memo_path}")


if __name__ == "__main__":
    main()
