from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from config import RESULTS_DIR

STORE = RESULTS_DIR / "experiments.jsonl"
MEMO_DIR = RESULTS_DIR / "memos"
MEMO_DIR.mkdir(exist_ok=True)


def read_experiments() -> list[dict]:
    if not STORE.exists():
        return []
    rows: list[dict] = []
    with STORE.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_experiment(result: dict) -> int:
    rows = read_experiments()
    experiment_id = len(rows) + 1
    record = {
        "experiment_id": experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **result,
    }
    with STORE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return experiment_id


def save_memo(question: str, memo: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = MEMO_DIR / f"memo_{timestamp}.md"
    body = f"# Alpha Research Memo\n\n## Research question\n\n{question}\n\n## Agent memo\n\n{memo}\n"
    path.write_text(body, encoding="utf-8")
    (RESULTS_DIR / "latest_memo.md").write_text(body, encoding="utf-8")
    return path


def reset_store() -> None:
    if STORE.exists():
        STORE.unlink()
