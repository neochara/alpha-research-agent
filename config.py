from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Nine long-history U.S. sector ETFs. Deliberately fixed for the first version.
UNIVERSE = [
    "XLB", "XLE", "XLF", "XLI", "XLK",
    "XLP", "XLU", "XLV", "XLY",
]

START_DATE = "2005-01-01"
END_DATE = None

# Research protocol: tune on train/validation; keep test sealed until final evaluation.
TRAIN_END = "2018-12-31"
VALID_END = "2022-12-31"

DEFAULT_COST_BPS = 5.0
TRADING_DAYS = 252
MAX_EXPERIMENTS_PER_RUN = 8
