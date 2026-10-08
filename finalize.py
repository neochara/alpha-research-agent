from __future__ import annotations

import argparse
import json

from backtest import ExperimentSpec, evaluate
from data import load_prices
from research_store import read_experiments


def evaluate_test(experiment_id: int) -> dict:
    """Human-controlled final gate; intentionally not exposed as an agent tool."""
    rows = read_experiments()
    matches = [x for x in rows if x["experiment_id"] == experiment_id]
    if not matches:
        raise ValueError(f"Unknown experiment_id={experiment_id}")

    spec = ExperimentSpec(**matches[0]["spec"])
    return evaluate(load_prices(), spec, include_test=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate one pre-selected experiment on the held-out test period."
    )
    parser.add_argument("experiment_id", type=int)
    args = parser.parse_args()
    print(json.dumps(evaluate_test(args.experiment_id), indent=2))


if __name__ == "__main__":
    main()
