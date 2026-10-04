# Learning Log

## Week 1 Day 1 (Fri Oct 2, finished Sat Oct 3): Claude Code basics

**Learn:** How Claude Code works: CLAUDE.md memory, plan mode, /clear vs /compact, reviewing diffs.
Check questions: 4 / 6.
- CLAUDE.md loads from the launch folder **and every parent folder** (both my portfolio and AI Learning files load). Child-folder CLAUDE.md files load only when Claude works there.
- Plan mode is read-only: use it for multi-step, multi-file or unclear tasks; skip it for small obvious edits. Planning costs tokens up front but is cheaper than rework.
- `/clear` wipes context (use between unrelated tasks); `/compact` summarizes it (use when a long session is still on the same task). Every message resends the whole conversation, so stale context burns Pro quota.

**Build:**
- Created public GitHub repo `dilips24/ai-builder-portfolio` and pushed the initial commit.
- Used Claude Code (Sonnet, plan mode) to write `day01/token_estimator.py`: 8 synthetic change-request questions, chars/4 token estimate, Haiku input cost.
- Committed and pushed myself: `Day 1: token estimator script`.

**Numbers:** 8 questions, 339 chars, ~89 estimated tokens, ~$0.000089 estimated Haiku input cost (at $1.00 per million input tokens).

**What broke and how I fixed it:**
- PowerShell would not run `Activate.ps1` by name. Fix: allow local scripts once (`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`), then run scripts with a path (`.\Activate.ps1`, or `..\.venv\Scripts\Activate.ps1` from the portfolio folder). PowerShell never runs scripts from the current folder without `.\`.

**Next:** Day 2 compares this chars/4 estimate with the real token counts the API returns.

## Week 1 Day 2 (Sat Oct 3): Messages API, tokens and cost

**Learn:** Messages API: model, system, messages (user/assistant roles), max_tokens, usage. Check questions: 4.5 / 6.
- The API is stateless: every call resends the system prompt plus the full message history, so input cost grows with every turn. Fixes: cap history, summarize old turns, prompt caching.
- `max_tokens` is a ceiling, not a target. The real lever on output cost is the instruction ("Answer in 2-3 sentences"). Prompt caching helps only once the repeated context is large. Cheapest token is the one you don't send: route known questions to rules.
- Claude Pro = flat-rate use by me; the API = metered use by my code. A spend limit guards against runaway loops and a leaked key, so it goes in before any code.

**Build:**
- Console account, $5 credit, monthly spend limit, API key in a git-ignored `.env` (verified: not tracked, not in Git history).
- `day02/first_call.py`: calls `claude-haiku-4-5`, prints answer, input/output tokens, latency and cost; `--no-system` flag; reuses the Day 1 estimator.

**Numbers** (question: "What's the lead time for a normal change?"):

| | With system prompt | No system prompt |
|---|---|---|
| Input tokens | 39 | 17 |
| Output tokens | 71 | 260 |
| Latency | 1,636 ms | 3,124 ms |
| Cost | $0.000394 | $0.001317 |

- The system prompt cost 22 input tokens and saved 189 output tokens: 3.3x cheaper and about 2x faster. At 10,000 questions/day: ~$3.94 vs ~$13.17.
- Day 1 chars/4 estimate for the question was ~11 tokens; the API counted 17. Use `usage` for real numbers.
- Latency tracks output length: shorter answers are cheaper and faster.

**What broke:** `pip freeze > requirements.txt` in PowerShell wrote the file as UTF-16. Fix: `pip freeze | Set-Content -Encoding ascii requirements.txt`.

**Next:** Day 3: 20 synthetic change-request FAQs and a prompt that classifies questions into categories as JSON with a confidence score.

## Week 1 Day 3 (Sun Oct 4): Classifying FAQs as JSON, prompt vs structured outputs

**Build:**
- `day03/faqs.json`: 20 synthetic change-request questions across 8 categories (incl. `out_of_scope`), with typos and lowercase phrasing mixed in.
- `day03/classify.py --mode prompt|schema`: classifies each FAQ into category + confidence + reason with `claude-haiku-4-5`, temperature 0. Logs validity, correctness, tokens, latency and cost per question to `results_<mode>.csv`.
  - `prompt`: JSON requested only in the system prompt, parsed with `json.loads`.
  - `schema`: native structured outputs (`client.messages.parse` with a Pydantic model, `category` is a `Literal`).
- `day03/day03_prompt_vs_schema.xlsx`: side-by-side of the two runs.

**Numbers** (20 questions each):

| | Prompt-only JSON | Structured outputs |
|---|---|---|
| Valid JSON | 1/20 | 20/20 |
| Accuracy (as scored by the script) | 1/20 (5%) | 20/20 (100%) |
| Input tokens (total) | 5,755 | 10,475 |
| Output tokens (total) | 1,033 | 1,004 |
| Avg latency | 914 ms | 1,203 ms |
| Total cost | $0.010920 | $0.015495 |

- Prompt mode failed 19/20 because Haiku wrapped the JSON in ```` ```json ```` fences even though the prompt said "no markdown, no code fences, first character must be {". The category in the raw output was the expected one every time, so the model classified fine; only the format broke `json.loads`. Real accuracy is hidden behind the parse failure.
- Structured outputs cost ~42% more in this run (~523 vs ~288 input tokens per call; output tokens about equal). Latency was higher too, though the first schema call (1,926 ms) is an outlier that pulls the average up.
- Confidence is not very informative here: mostly 0.95 in both modes. The one low score was faq-20 in prompt mode (0.65, rollback vs CAB overlap), which the schema run scored 0.85.

**What broke:** prompt-only JSON, as above. Fix: structured outputs, or strip fences before parsing if staying with prompt mode.

**Decision:** use structured outputs wherever code consumes the model's JSON.

## Week 1 Day 3 (Sun Oct 4): Prompt design and structured JSON output

**Learn:** Structured outputs (`output_config` / `client.messages.parse` with a Pydantic model), schema as a contract, self-reported confidence. Check questions: 1.75 / 3.
- `enum` (a `Literal` in Pydantic) limits a field's *values*; `additionalProperties: false` blocks extra *keys*; `required` blocks missing keys. A prompt-only approach can't enforce any of these: `json.loads` only checks syntax.
- Model confidence is self-reported, not a probability. A routing threshold (e.g. 0.7) has to be calibrated against labeled data: compare confidence on correct vs wrong answers.
- Structured outputs guarantees the *format*, not the *correctness*: a valid, allowed category can still be the wrong one. Schemas make output safe to parse; evals tell you whether it's safe to trust.

**Build:**
- `day03/faqs.json`: 20 synthetic change-request FAQs, labeled across 8 categories (incl. `out_of_scope` and ambiguous questions).
- `day03/classify.py`: classifies each question as `{category, confidence, reason}` with `claude-haiku-4-5`, temperature 0. `--mode prompt` (JSON requested in the system prompt, parsed with `json.loads`) vs `--mode schema` (native structured outputs). Saves `results_<mode>.csv`.
- `day03/day03_prompt_vs_schema.xlsx`: side-by-side comparison.

**Numbers:**

| | Prompt only | Schema |
|---|---|---|
| Valid JSON | 1/20 | 20/20 |
| Accuracy | 1/20 (5%) | 20/20 (100%) |
| Input tokens / question | 288 | 524 |
| Output tokens / question | 52 | 50 |
| Cost / question | $0.00055 | $0.00077 (+42%) |
| Avg latency | 914 ms | 1,203 ms |
| First call | 1,183 ms | 1,926 ms |

- Schema mode adds ~236 input tokens per call: about +42% cost (~$7.75 vs ~$5.46 per 10,000 questions).
- The first schema call is slowest while the schema compiles (cached 24 h).
- 100% on 20 Claude-written questions likely means the test set is too easy. All confidences were 0.85-1.00 with no misses, so the threshold can't be calibrated yet.

**What broke:** Prompt mode failed 19/20 because Haiku wrapped the JSON in ```json code fences, despite an explicit "no code fences" instruction. The classifications inside were correct: a parsing failure, not a reasoning failure. Kept as the baseline; structured outputs is the fix.

**Carried over:** Task C: add 6 harder, real-world-phrased questions (faq-21 to faq-26) and check whether misses carry lower confidence.

**Next:** Day 4: router: keyword rules answer known questions, everything else goes to the LLM; log path, latency and tokens.
