# GitHub Setup

> **Updating an existing local copy?** Preserve your local `.env` file, replace the rest of the repository with the new package, then run `pip install -r requirements-dev.txt` again. The distributed zip intentionally does not contain a real `.env` file, so your API key is not overwritten.

# Publishing this project to GitHub

## 1. Create the repository on GitHub

On GitHub, choose **New repository** and use a name such as:

`alpha-research-agent`

A suitable short description is:

> LLM-driven quantitative research agent for controlled cross-sectional momentum experiments with deterministic backtesting and sealed out-of-sample evaluation.

If this folder already contains the README, `.gitignore`, and license, do **not** ask GitHub to generate additional copies when creating the empty repository.

## 2. Initialize Git locally

From the project directory:

```bash
git init
git add .
git commit -m "Initial Alpha Research Agent release"
```

## 3. Connect the local repository to GitHub

Replace `<YOUR-USERNAME>` with your GitHub username:

```bash
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/alpha-research-agent.git
git push -u origin main
```

If GitHub asks for authentication, use the method configured for your account (for example GitHub CLI, SSH, or a personal access token). Password authentication for Git over HTTPS is not the normal workflow.

## 4. Never commit an API key

The repository includes `.env.example`, but `.env` is ignored. Create your local file with:

```bash
cp .env.example .env
```

Then add your real `OPENAI_API_KEY` only to `.env`.

Before pushing, a useful check is:

```bash
git status
```

The real `.env` file should **not** appear among the files to be committed.

## 5. Verify the repository before sharing it

Run:

```bash
pytest -q
python run.py --reset
```

Then check that the GitHub README renders correctly, including the Mermaid diagrams.

## 6. Suggested GitHub topics

`agents`, `quantitative-finance`, `algorithmic-trading`, `momentum`, `backtesting`, `openai-agents`, `python`, `llm-agents`, `research`

## 7. Good next commits

Keep future changes small and legible. Examples:

```text
Add walk-forward validation
Add factor-neutral portfolio construction
Add point-in-time equity universe
Add experiment dashboard
Add critic agent
```

This makes the repository history itself useful evidence of how the system developed.

## Optional: verify the FastAPI service before pushing

```bash
fastapi dev
```

Open `http://127.0.0.1:8000/docs` and try `GET /health`. Stop the server with `Ctrl+C` before continuing.
