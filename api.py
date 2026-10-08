from __future__ import annotations

import threading
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from agent import run_research
from config import TRAIN_END, VALID_END
from data import download_prices, load_prices
from research_store import read_experiments, reset_store

load_dotenv(override=True)

app = FastAPI(
    title="Alpha Research Agent API",
    version="1.0.0",
    description=(
        "HTTP interface for the Alpha Research Agent. The API exposes research "
        "and experiment-inspection endpoints, while the held-out test remains a "
        "separate human-controlled CLI step."
    ),
)

# The current research store and session counter are process-local/stateful.
# Serialize research requests so two agent runs cannot interleave experiments.
_research_lock = threading.Lock()


class ResearchRequest(BaseModel):
    question: str = Field(min_length=8, description="Plain-English quantitative research question.")
    reset: bool = Field(
        default=False,
        description="Clear prior local experiment history before this research run.",
    )
    refresh_data: bool = Field(
        default=False,
        description="Force a fresh Yahoo Finance download before the run.",
    )
    model: str | None = Field(
        default=None,
        description="Optional OpenAI model override. Otherwise use AGENT_MODEL or the SDK default.",
    )


class ResearchResponse(BaseModel):
    question: str
    memo: str
    memo_path: str
    experiments_run: int


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "Alpha Research Agent API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dataset")
def dataset() -> dict[str, Any]:
    prices = load_prices()
    return {
        "assets": list(prices.columns),
        "start": str(prices.index.min().date()),
        "end": str(prices.index.max().date()),
        "rows": len(prices),
        "missing_fraction_by_asset": {
            c: round(float(prices[c].isna().mean()), 4) for c in prices.columns
        },
        "protocol": {
            "train": f"through {TRAIN_END}",
            "validation": f"after {TRAIN_END} through {VALID_END}",
            "test": f"after {VALID_END}; sealed during research",
        },
    }


@app.get("/experiments")
def experiments() -> dict[str, Any]:
    rows = read_experiments()
    return {"count": len(rows), "experiments": rows}


@app.post(
    "/research",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
)
def research(request: ResearchRequest) -> ResearchResponse:
    acquired = _research_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another research run is already in progress. Try again after it finishes.",
        )

    try:
        if request.reset:
            reset_store()

        before = len(read_experiments())
        download_prices(force=request.refresh_data)
        memo, memo_path = run_research(request.question, model=request.model)
        after = len(read_experiments())

        return ResearchResponse(
            question=request.question,
            memo=memo,
            memo_path=memo_path,
            experiments_run=max(0, after - before),
        )
    finally:
        _research_lock.release()
