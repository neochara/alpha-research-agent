# Alpha Research Agent

A small quantitative research agent for testing cross-sectional momentum ideas on a sector ETF universe.

The project combines:

- LLM-based research reasoning
- deterministic Python backtesting
- experiment tracking
- train / validation / held-out test separation
- transaction-cost modeling
- statistical diagnostics
- a simple browser interface
- a FastAPI JSON API

The main idea is that the language model decides **what to test**, while deterministic Python code performs the actual calculations.

---

## What the agent does

Given a research question such as:

> Does 6-month momentum work?

the agent can:

1. interpret the research question;
2. generate a small number of testable momentum specifications;
3. run deterministic backtests;
4. compare training and validation performance;
5. account for turnover and transaction costs;
6. compute performance and statistical diagnostics;
7. reject weak or unsupported specifications;
8. return a concise research memo;
9. save the experiment history and memo locally.

The held-out test period is deliberately excluded from the normal research loop.

---

## Research workflow

```text
Research question
        ↓
Generate testable hypotheses
        ↓
Choose experiment parameters
        ↓
Run deterministic backtests
        ↓
Evaluate training + validation results
        ↓
Compare robustness, turnover, costs, statistics
        ↓
Select or reject candidate
        ↓
Generate research memo
```

The LLM does not calculate returns, Sharpe ratios, turnover, or statistical tests itself.

Those calculations are performed by the Python backtesting code.

---

## Example research questions

Examples include:

```text
Does 6-month momentum work?
```

```text
Does 12-month momentum outperform 6-month momentum?
```

```text
Find a simple, robust cross-sectional momentum signal in the available sector ETF universe.
```

The current version intentionally limits the research space to momentum-style experiments supported by the available tools.

---

## Data

The project currently uses nine U.S. sector ETFs:

```text
XLB
XLE
XLF
XLI
XLK
XLP
XLU
XLV
XLY
```

Historical price data is downloaded using `yfinance`.

Using sector ETFs keeps the first version of the project relatively simple while providing a cross-sectional universe with long historical coverage.

---

## Data split

The research protocol separates the data into:

```text
Training:
through 2018-12-31

Validation:
2019-01-01 through 2022-12-31

Held-out test:
2023 onward
```

The agent can use the training and validation periods while developing and comparing hypotheses.

The held-out test period is intentionally kept outside the automated research loop.

This reduces the risk of repeatedly adapting the strategy to the final evaluation period.

---

## Momentum signals

A simple cross-sectional momentum score can be written as

```text
momentum = past price / earlier price - 1
```

For example, a 6-month momentum signal uses approximately 126 trading days of price history.

The ETFs are ranked according to their momentum scores.

Recent relative winners can then be selected for the portfolio.

Some specifications also use a skip period.

For example:

```text
252-day lookback
21-day skip
```

approximately corresponds to a 12-1 momentum signal: performance over roughly the previous twelve months while excluding the most recent month.

---

## Research safeguards

The project includes several safeguards intended to make the experiments more disciplined.

### Maximum experiment count

The agent is limited to a small number of experiments per research run.

This helps reduce automated specification searching and backtest overfitting.

### Held-out test protection

The main research agent does not access the held-out test set.

Final test evaluation is performed separately through `finalize.py`.

### Transaction costs

Backtests include configurable transaction costs.

Both gross and net performance can therefore be examined.

### Turnover

Portfolio turnover is tracked to show how aggressively a strategy trades.

### Statistical diagnostics

The project reports statistical diagnostics including:

- naive return t-statistics;
- HAC / Newey-West-style t-statistics.

These statistics are diagnostics rather than proof that a trading strategy is profitable.

---

## Project structure

```text
alpha-research-agent/
├── agent.py
├── api.py
├── backtest.py
├── config.py
├── data.py
├── finalize.py
├── research_store.py
├── run.py
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── tests/
│   ├── conftest.py
│   ├── test_backtest.py
│   └── test_api.py
├── .github/
│   └── workflows/
│       └── tests.yml
└── docs/
    ├── GITHUB_SETUP.md
    ├── alpha_research_agent_guide.pdf
    └── images/
        ├── workflow.png
        └── data_split.png
```

---

## Main files

### `agent.py`

Defines the research agent and the tools available to it.

The agent decides which supported experiments to run and interprets the resulting statistics.

### `backtest.py`

Contains deterministic portfolio and backtesting logic.

This is where returns, portfolio weights, transaction costs, turnover, and statistical metrics are calculated.

### `data.py`

Downloads and prepares the ETF price data.

### `research_store.py`

Stores experiment history so research runs can be inspected later.

### `run.py`

Command-line entry point for running the research agent.

### `finalize.py`

Runs the deliberately separate held-out test evaluation.

### `api.py`

Provides:

- a browser-based research interface;
- a FastAPI JSON API;
- dataset and experiment inspection endpoints;
- interactive Swagger API documentation.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/neochara/alpha-research-agent.git
cd alpha-research-agent
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

---

## OpenAI API key

Copy the example environment file:

```bash
cp .env.example .env
```

Then edit `.env` and add your OpenAI API key:

```text
OPENAI_API_KEY=your_api_key_here
```

The `.env` file is excluded by `.gitignore` and should not be committed to GitHub.

---

## Run from the command line

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Then run:

```bash
python run.py
```

To reset the previous research history before starting:

```bash
python run.py --reset
```

The agent will run its experiments and generate a research memo.

Generated memos are stored under:

```text
results/memos/
```

The latest memo is also stored at:

```text
results/latest_memo.md
```

---

## Run the browser interface

Start FastAPI with:

```bash
python -m fastapi dev
```

Then open:

```text
http://127.0.0.1:8000
```

This is the human-facing interface.

Enter a research question in the text box and click:

```text
Run research
```

The result is displayed as a formatted research memo in the browser and is also saved locally.

---

## API documentation

FastAPI automatically generates interactive API documentation.

Open:

```text
http://127.0.0.1:8000/docs
```

This opens the Swagger UI.

Swagger allows you to inspect and test the API endpoints directly from the browser.

The OpenAPI specification is available at:

```text
http://127.0.0.1:8000/openapi.json
```

---

## API endpoints

The current API exposes:

```text
GET  /
```

Human-facing browser interface.

```text
GET  /health
```

Basic server health check.

```text
GET  /dataset
```

Information about the dataset and research protocol.

```text
GET  /experiments
```

View stored experiment information.

```text
POST /research
```

Run the research agent through a JSON API request.

```text
POST /research-ui
```

Form endpoint used by the browser interface.

The held-out test is intentionally not exposed through the API.

---

## Example JSON API request

A request to:

```text
POST /research
```

can contain:

```json
{
  "question": "Does 6-month momentum work?"
}
```

The response contains:

```json
{
  "memo": "...",
  "memo_path": "..."
}
```

This allows other programs, notebooks, front ends, or services to call the same research agent.

---

## Browser UI vs API

There are two ways to interact with the project.

### Browser UI

Use:

```text
http://127.0.0.1:8000
```

This is intended for a human user.

You type a normal research question into a text box and receive a formatted memo.

### JSON API

Use:

```text
http://127.0.0.1:8000/docs
```

or call the HTTP endpoints programmatically.

This is useful when another application wants to communicate with the agent.

---

## Run tests

Run:

```bash
pytest -q
```

For more detailed output:

```bash
pytest -v
```

The tests are intended to check software and research correctness rather than whether a strategy is profitable.

Examples include checks that:

- momentum signals only use past information;
- portfolio construction behaves as expected;
- transaction costs are applied correctly;
- same-day look-ahead bias is avoided;
- API routes behave correctly.

---

## Continuous integration

The repository includes a GitHub Actions workflow.

On pushes and pull requests, GitHub creates a temporary environment, installs the project dependencies, and runs the test suite.

This provides an automated check that changes do not break the existing implementation.

---

## Final held-out evaluation

The held-out test period should only be examined after selecting a final specification.

This is intentionally performed outside the main agent loop.

A selected experiment can be evaluated using:

```bash
python finalize.py <experiment_id>
```

The purpose of this separation is to prevent the agent from repeatedly observing and adapting to the test period.

---

## Research outputs

A typical research memo contains:

- hypothesis;
- dataset and protocol;
- experiments tested;
- training results;
- validation results;
- turnover;
- transaction costs;
- Sharpe ratio;
- statistical diagnostics;
- best candidate, if any;
- caveats;
- recommended next test.

The agent is allowed to conclude that none of the tested specifications provide convincing evidence.

A negative result is a valid research outcome.

---

## Important limitations

This project is an educational and research prototype.

Important limitations include:

- a small ETF universe;
- limited strategy families;
- historical backtesting only;
- simplified trading-cost assumptions;
- no live execution;
- no broker integration;
- no guarantee that historical patterns persist;
- multiple-testing and backtest-overfitting risk;
- statistical uncertainty from relatively short validation periods.

The project should not be interpreted as investment advice or as evidence that any strategy will be profitable in live markets.

---

## Design philosophy

The project intentionally separates the responsibilities of the language model and the quantitative engine.

The language model handles tasks such as:

```text
What should I test?
Which experiment should come next?
What does the evidence suggest?
What are the caveats?
```

Deterministic Python handles tasks such as:

```text
What were the returns?
What was the turnover?
What transaction costs were incurred?
What was the Sharpe ratio?
What was the t-statistic?
```

This separation makes the research process easier to inspect and reproduce than allowing the language model to directly invent quantitative results.

---

## Technology

The project currently uses:

- Python
- OpenAI Agents SDK
- FastAPI
- Pydantic
- pandas
- NumPy
- SciPy
- yfinance
- Markdown
- pytest
- GitHub Actions

---

## Disclaimer

This repository is intended for research, educational, and demonstration purposes only.

It is not investment advice and should not be used as the sole basis for financial decisions.