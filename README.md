# AI Builder Portfolio

Projects from a 7-week AI Builder plan: hands-on AI features built with Python and the Claude API, each measured with its own evaluation. All data is synthetic (ITSM / change-and-release / telecom domain).

## Projects

| # | Project | What it shows | Status | Stack |
|---|---|---|---|---|
| 1 | [Change Request FAQ Agent](change-request-faq-agent/) | Rules vs LLM routing, grounding in a policy, hand-graded eval with a blind holdout, cost per useful answer | Done | Python, Claude Haiku 4.5, Streamlit |
| 2 | Incident Runbook Assistant (RAG) | Retrieval over synthetic runbooks and postmortems, cited answers, "I don't know" handling, retrieval and answer evals | In progress | Python, Claude, ChromaDB, Streamlit |

### Project 1 headline

On 14 new questions the rules were never tuned on, a rules-first router gave useful answers 57% of the time vs 89% for an all-LLM design. The router looked 36% cheaper per question, but **cost per useful answer was identical ($0.00188)**. Details, architecture diagram and full results: [change-request-faq-agent/README.md](change-request-faq-agent/README.md).

## Repo layout

- One folder per project, each with its own README, Mermaid architecture diagram and results table.
- `LEARNING_LOG.md`: one entry per session (what worked, what broke, numbers measured) and the weekly check-in scores. Entries before Oct 12 refer to `dayNN` paths, which now live inside `change-request-faq-agent/`.
- Shared at the root: `requirements.txt` and a git-ignored `.env` with `ANTHROPIC_API_KEY`.
