# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Public GitHub portfolio for the 7-week AI Builder plan (Oct 2 – Dec 6, 2026 target; 51 numbered sessions): 3 projects plus a capstone (PRD Genie). Each project lives in its own folder with a README, a Mermaid architecture diagram and an eval/results table. The full schedule is in `../AI Builder Plan 7 Weeks, 3 Hrs a Day.md`.

## Current goal

Week 1 (Sessions 1–9; Session 6 = Oct 11): **Change Request FAQ Agent**. Keyword rules answer known questions instantly; anything else goes to the LLM. Log path, latency, tokens and cost per question. Then start the Week 2 **Incident Runbook Assistant** (RAG over 15–20 synthetic runbooks, ChromaDB, cited answers).

Update this section as the weeks progress.

## Tooling

- Editor: Cursor. Claude Code runs in Cursor's integrated terminal (Windows, PowerShell); Cursor's own AI agent is not used.
- Give shell commands in PowerShell syntax. Scripts in the current folder need a path, e.g. `.\script.ps1`.
- The user commits and pushes himself; do not run `git commit` or `git push` unless asked.

## Stack

- Python (use the `.venv` in `C:\AI Learning`: `..\.venv\Scripts\Activate.ps1` from this folder, `..\..\.venv\Scripts\Activate.ps1` from a project folder)
- Anthropic API: Haiku while developing, to keep cost low
- Streamlit for UIs, ChromaDB for vector search
- Later: FastAPI, LangChain, LangGraph, CrewAI

Project 1 lives in `change-request-faq-agent\` (its build steps are the `day01`-`day06` subfolders; scripts find each other and the root `.env` by paths relative to their own file, so they run from any folder). From `change-request-faq-agent\`: `python day01\token_estimator.py`; the Streamlit FAQ app: `streamlit run day05\app.py` (venv active); evaluate with `python day06\eval.py` (prints the LLM-call count and estimated cost, asks to confirm; `--yes` skips the prompt; ~55 Haiku calls, ~$0.09; writes `day06\results.csv` with `useful` blank for hand grading Y/P/N), then `python day06\summarize.py` (no API calls; reads the graded CSV, writes `day06\summary.md`). Project 2 lives in `runbook-assistant\`. New projects get their own top-level folder, not `dayNN` folders. No build, lint or test commands exist yet. Add them here when a project introduces them, including how to run a single test or eval.

## Conventions

- API keys live in a git-ignored `.env`. Confirm `.gitignore` covers `.env` before the first commit that touches it.
- Every app logs, per request: path taken (rules vs LLM), latency, input/output tokens and cost.
- Data is synthetic and uses an ITSM / change-and-release / telecom domain. Never add real employer or customer data.
- Each project README needs a Mermaid architecture diagram and a results table (accuracy, latency, cost).
- Keep one project per top-level folder so each can be explained and demoed on its own.

## Learning log

`LEARNING_LOG.md` holds one entry per day: what worked, what broke, numbers measured. Drafts are written from the user's notes; do not invent results.
