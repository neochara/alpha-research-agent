from __future__ import annotations

from html import escape

import markdown
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent import describe_dataset, list_experiments, run_research


# Prefer the API key stored in this project's .env file
# over any older key exported in the terminal session.
load_dotenv(override=True)


app = FastAPI(
    title="Alpha Research Agent API",
    version="1.0.0",
    description=(
        "HTTP interface for the Alpha Research Agent. "
        "The API exposes research and experiment-inspection endpoints, "
        "while the held-out test remains a separate human-controlled CLI step."
    ),
)


# ---------------------------------------------------------------------
# Pydantic models used by the JSON API
# ---------------------------------------------------------------------

class ResearchRequest(BaseModel):
    question: str


class ResearchResponse(BaseModel):
    memo: str
    memo_path: str


# ---------------------------------------------------------------------
# HTML helper
# ---------------------------------------------------------------------

def page_template(body: str, title: str = "Alpha Research Agent") -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>{escape(title)}</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Roboto,
                Helvetica,
                Arial,
                sans-serif;

            background: #f7f7f8;
            color: #1f2937;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 48px 24px 80px;
        }}

        h1 {{
            margin-bottom: 8px;
            font-size: 34px;
        }}

        h2 {{
            margin-top: 32px;
        }}

        h3 {{
            margin-top: 26px;
        }}

        p {{
            line-height: 1.65;
        }}

        li {{
            line-height: 1.65;
            margin-bottom: 5px;
        }}

        .subtitle {{
            color: #6b7280;
            margin-bottom: 32px;
            line-height: 1.5;
        }}

        .card {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 24px;
            margin-top: 20px;
        }}

        textarea {{
            width: 100%;
            min-height: 150px;
            resize: vertical;

            padding: 14px;

            font-family: inherit;
            font-size: 16px;
            line-height: 1.5;

            border: 1px solid #d1d5db;
            border-radius: 8px;
        }}

        textarea:focus {{
            outline: none;
            border-color: #111827;
        }}

        button {{
            margin-top: 14px;
            padding: 11px 18px;

            border: none;
            border-radius: 8px;

            font-size: 15px;
            font-weight: 600;

            background: #111827;
            color: white;

            cursor: pointer;
        }}

        button:hover {{
            opacity: 0.9;
        }}

        .memo {{
            line-height: 1.65;

            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;

            padding: 24px;
            margin-top: 20px;
        }}

        .memo h1,
        .memo h2,
        .memo h3 {{
            margin-top: 24px;
        }}

        .memo h1:first-child,
        .memo h2:first-child,
        .memo h3:first-child {{
            margin-top: 0;
        }}

        .path {{
            margin-top: 16px;
            color: #6b7280;
            font-size: 13px;
            word-break: break-all;
        }}

        .nav {{
            margin-bottom: 24px;
        }}

        .nav a {{
            color: #2563eb;
            text-decoration: none;
            margin-right: 18px;
        }}

        .nav a:hover {{
            text-decoration: underline;
        }}

        code {{
            background: #f3f4f6;
            padding: 2px 5px;
            border-radius: 4px;
        }}
    </style>
</head>

<body>
    <div class="container">
        {body}
    </div>
</body>
</html>
"""


# ---------------------------------------------------------------------
# Human-facing browser UI
# ---------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root():
    body = """
        <h1>Alpha Research Agent</h1>

        <p class="subtitle">
            Enter a quantitative research question.
            The agent will design a small number of controlled momentum
            experiments, evaluate them on training and validation data,
            and return a research memo.
        </p>

        <div class="nav">
            <a href="/docs">API documentation</a>
            <a href="/dataset">Dataset</a>
            <a href="/experiments">Experiments</a>
        </div>

        <div class="card">
            <form action="/research-ui" method="post">

                <label for="question">
                    <strong>Research question</strong>
                </label>

                <br><br>

                <textarea
                    id="question"
                    name="question"
                    required
                    placeholder="For example: Find a simple, robust cross-sectional momentum signal in the available sector ETF universe."
                ></textarea>

                <br>

                <button type="submit">
                    Run research
                </button>

            </form>
        </div>
    """

    return page_template(body)


@app.post("/research-ui", response_class=HTMLResponse)
def research_ui(question: str = Form(...)):
    memo, memo_path = run_research(question)

    safe_question = escape(question)
    safe_path = escape(str(memo_path))

    rendered_memo = markdown.markdown(
        memo,
        extensions=["extra"],
    )

    body = f"""
        <div class="nav">
            <a href="/">← New research question</a>
            <a href="/docs">API documentation</a>
        </div>

        <h1>Research Result</h1>

        <div class="card">
            <strong>Question</strong>
            <p>{safe_question}</p>
        </div>

        <h2>Research memo</h2>

        <div class="memo">
            {rendered_memo}
        </div>

        <div class="path">
            Saved memo:
            <code>{safe_path}</code>
        </div>
    """

    return page_template(
        body,
        title="Research Result — Alpha Research Agent",
    )


# ---------------------------------------------------------------------
# Programmatic JSON API
# ---------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "alpha-research-agent",
    }


@app.get("/dataset")
def dataset():
    """
    Return information about the available dataset and research protocol.
    """
    return describe_dataset()


@app.get("/experiments")
def experiments():
    """
    Return experiments stored by the research agent.
    """
    return list_experiments()


@app.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest):
    """
    Run the Alpha Research Agent through the JSON API.

    This endpoint is intended for programmatic access.
    Human users can instead use the browser UI at `/`.
    """
    memo, memo_path = run_research(request.question)

    return ResearchResponse(
        memo=memo,
        memo_path=str(memo_path),
    )