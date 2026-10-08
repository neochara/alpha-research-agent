from __future__ import annotations

import json
import os

from agents import Agent, Runner
from agents.decorators import tool

from backtest import ExperimentSpec, evaluate
from config import MAX_EXPERIMENTS_PER_RUN
from data import load_prices
from research_store import append_experiment, read_experiments, save_memo

_SESSION_START_COUNT = 0


@tool
def describe_dataset() -> str:
    """Describe the available dataset and research split without exposing test results."""
    prices = load_prices()
    info = {
        "assets": list(prices.columns),
        "start": str(prices.index.min().date()),
        "end": str(prices.index.max().date()),
        "rows": len(prices),
        "missing_fraction_by_asset": {
            c: round(float(prices[c].isna().mean()), 4) for c in prices.columns
        },
        "protocol": {
            "train": "through 2018-12-31",
            "validation": "2019-01-01 through 2022-12-31",
            "test": "2023-01-01 onward; SEALED during research",
        },
    }
    return json.dumps(info, indent=2)


@tool
def run_momentum_experiment(
    lookback_days: int,
    skip_days: int,
    rebalance_days: int,
    long_fraction: float,
    cost_bps: float,
    vol_scale: bool,
    vol_lookback: int = 63,
) -> str:
    """Run one deterministic cross-sectional momentum experiment.

    Only training and validation metrics are returned. The held-out test period is
    deliberately inaccessible to the agent.
    """
    already_run = len(read_experiments()) - _SESSION_START_COUNT
    if already_run >= MAX_EXPERIMENTS_PER_RUN:
        return json.dumps(
            {
                "error": "experiment_budget_exhausted",
                "message": (
                    f"This research run is limited to {MAX_EXPERIMENTS_PER_RUN} experiments "
                    "to reduce open-ended parameter searching. Conclude from the evidence available."
                ),
            },
            indent=2,
        )

    prices = load_prices()
    spec = ExperimentSpec(
        lookback_days=lookback_days,
        skip_days=skip_days,
        rebalance_days=rebalance_days,
        long_fraction=long_fraction,
        cost_bps=cost_bps,
        vol_scale=vol_scale,
        vol_lookback=vol_lookback,
    )
    result = evaluate(prices, spec, include_test=False)
    experiment_id = append_experiment(result)
    return json.dumps({"experiment_id": experiment_id, **result}, indent=2)


@tool
def list_experiments() -> str:
    """List experiments from the current research session."""
    rows = read_experiments()[_SESSION_START_COUNT:]
    return json.dumps(rows, indent=2)


INSTRUCTIONS = """
You are AlphaLab, a careful quantitative research agent.

GOAL
Investigate a user-supplied cross-sectional momentum question with deterministic
research tools and produce a concise evidence-based research memo.

NON-NEGOTIABLE RESEARCH RULES
1. Never claim performance that did not come from a tool result.
2. The test set is sealed. Select candidates using training and validation only.
3. Treat repeated parameter search as multiple testing / researcher degrees of freedom.
4. Prefer small, interpretable experiment families over brute-force optimization.
5. Change one or two ideas at a time so experiments remain interpretable.
6. Never infer causality from a backtest.
7. Discuss turnover, transaction costs, sample size, instability, and overfitting.
8. A strategy that is strong in training but weak in validation is not a survivor.
9. Do not keep searching until a positive result appears. Negative results are valid.
10. Respect the hard experiment budget enforced by the tool.
11. Prefer HAC t-statistics to IID t-statistics when commenting on statistical evidence,
    while acknowledging that neither solves multiple testing or all dependence issues.

WORKFLOW
A. Call describe_dataset first.
B. Translate the research question into a falsifiable hypothesis.
C. State a compact experiment plan.
D. Run a sensible baseline.
E. Inspect both training and validation results.
F. Based on evidence, run a small number of targeted variants.
G. Call list_experiments before concluding.
H. Rank at most three surviving specifications. If none survive, say so.
I. End with a research memo containing:
   - hypothesis
   - data/protocol
   - experiments actually run
   - key findings
   - best candidate(s), if any
   - statistical and implementation caveats
   - what should be tested next
   - an explicit statement that the held-out test remains untouched

AVAILABLE DESIGN CHOICES
- lookback_days
- skip_days
- rebalance_days
- long_fraction
- cost_bps
- inverse-volatility position scaling (vol_scale)
- vol_lookback

Do not ask the user for parameters unless the question fundamentally requires them.
Choose reasonable defaults and investigate.
"""


def build_agent(model: str | None = None) -> Agent:
    kwargs = {
        "name": "AlphaLab",
        "instructions": INSTRUCTIONS,
        "tools": [describe_dataset, run_momentum_experiment, list_experiments],
    }
    selected_model = model or os.getenv("AGENT_MODEL")
    if selected_model:
        kwargs["model"] = selected_model
    return Agent(**kwargs)


def run_research(question: str, model: str | None = None) -> tuple[str, str]:
    global _SESSION_START_COUNT
    _SESSION_START_COUNT = len(read_experiments())

    result = Runner.run_sync(build_agent(model=model), question, max_turns=30)
    memo = str(result.final_output)
    memo_path = save_memo(question, memo)
    return memo, str(memo_path)
