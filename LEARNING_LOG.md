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

## Week 1 Day 4, part 1 (Thu Oct 8): Rules vs LLM, plus harder test questions

**Learn:** Routing: deterministic rules vs the LLM ("Building effective agents", Routing section). Check questions: 1 / 3.
- Plain-English picture: a receptionist with a printed FAQ sheet (rules) and an expert in the back office (LLM). The router decides who takes each question.
- Q1: Rules answer only on a single, unambiguous keyword match. Zero matches or 2+ matches go to the LLM. A confidently wrong rule answer is worse than a slower LLM answer, because no one sees it fail.
- Q2: Rules are free per call but not free to own. They copy the policy, so every policy change means a rules change; keyword lists sprawl unless someone owns, regression-tests and monitors them. Treat rules like a configuration item under change control.
- Q3: Move a category LLM → rules when it is high-volume, its LLM answers are repetitive and its policy is stable. Move it back when rule precision drops, most questions fall through anyway, or users keep re-asking.

**Build (Task A, carried over from Day 3):**
- Wrote 6 harder, real-world questions myself (faq-21 to faq-26) and added them to `day03/faqs.json`, each with a `why_tricky` note. They include keyword traps ("rollback" in a form question, "emergency" in a lead-time question) and an "urgent but not an emergency" case.
- Reran `python day03\classify.py --mode schema` on all 26.

**Numbers** (26 questions, schema mode):
- Accuracy 24/26 (92%), down from 20/20 on the easier set. Valid JSON 26/26.
- Misses: faq-21 (untested code to prod) → `change_types`, expected `cab_approval`: a **category gap**, no "testing/readiness" bin exists. faq-25 (certified Friday, needs weekend approval) → `emergency_change`, expected `lead_time_scheduling`: **urgent mistaken for an emergency**, which would push people to misuse the emergency process.
- Avg confidence 0.92 when right vs 0.85 when wrong. Five correct answers also scored 0.85; the lowest score (faq-23, 0.65) was correct. A 0.90 trust threshold would catch both errors but also flag 6 correct answers.
- Total cost $0.020336 (~$0.0008 per question), 14,964 tokens, avg latency 1,458 ms.

**What I learned:** Easy, Claude-written test questions hide weaknesses; real phrasing exposes them. Self-reported confidence is a weak signal: useful as a safety net, not trustworthy alone. Labelling is a judgment call where domain knowledge matters.

**To fix later:** Define "emergency" in the prompt/policy (something broken now vs business urgency), then test on new questions, not just faq-25, to avoid teaching to the test. Consider a testing/readiness category.

**Next:** Day 4 part 2 (Fri Oct 9): Task B, the router (`policy.md`, `rules.json`, `router.py`, `router_log.csv`).

## Week 1 Day 4, part 2 (Fri Oct 9): The router, and an honest holdout test

**Build:**
- `day04/policy.md`: one-page synthetic change policy (the shared "rulebook"). Defines emergency = something broken right now; business urgency = late/expedited normal change.
- `day04/rules.json`: keyword patterns + one canned answer per category (the "receptionist's FAQ sheet").
- `day04/router.py`: exactly one category matches → canned answer (`rule`); zero or 2+ → `claude-haiku-4-5` with policy.md as system prompt, "answer only from the policy" (`llm`). Logs path, matches, latency, tokens, cost. `--faqs` / `--out` options added for the holdout run.
- `day04/holdout.json`: 8 new questions I wrote without looking at the rules (hd-01 to hd-08).

**Numbers, seen questions** (26 FAQs from day03):
- Rules answered 20/26 (77%), right category 20/20, 0 ms, $0.
- LLM answered 6/26 (typo in faq-02 matched nothing; faq-19, 20, 22, 26 matched 2 categories; faq-21 matched none). Avg 1,139 ms, $0.0094 total (~$0.0016 each).
- All-LLM would have cost ~$0.041 → router ~77% cheaper. LLM calls cost ~2x Day 3 (~1,280 input tokens) because the whole policy goes with every question.
- faq-25 (urgent ≠ emergency) now correct, thanks to the emergency definition in policy.md.

**Catch:** Claude Code wrote rules.json and policy.md while looking at the 26 test questions (e.g. a "weekend" trigger for faq-25, policy sentences matching faq-19 and faq-24). The 100% was "seen the exam" — hence the holdout.

**Numbers, holdout** (8 unseen questions):

| | Seen (26) | Holdout (8) |
|---|---|---|
| Answered by rules | 77% | 38% (3/8) |
| Rule picked right category | 100% | 100% (3/3) |
| Rule answer actually answered the question | ~all | 1/3 |
| LLM invented facts | 0 | 0/5 |
| LLM honestly said "policy doesn't cover this" | – | 2/5 |

- LLM path: $0.0083 for 5 answers, avg 1,320 ms.
- hd-05 (which risk level?) and hd-08 (whom to inform on window overrun?) got the right-category paragraph that doesn't answer the question. Rules give one answer per category, not per question.
- hd-04 ("CRM screens freezed"): LLM avoided the word trap and gave the normal-vs-emergency nuance.
- hd-01 (find conflicting planned changes) needs live data lookup: a tool, not a FAQ (Week 4).

**My routing predictions:** 3/4 right (faq-06 rule, faq-19 LLM, faq-26 LLM). Missed faq-22: I predicted rule because it's really a form question, but "rollback" + "change form" matched 2 categories, so it went to the LLM. Lesson: the rules count keywords; they don't understand meaning.

**What I learned:**
- Always test on questions the builder hasn't seen; tuned rules overfit.
- "Right category" ≠ "user was helped". `rule_correct` measured the wrong thing; the metric that matters is answer usefulness (LLM-as-judge, Week 3).
- Grounding ("answer only from the policy") worked: no hallucinations, honest "I don't know" with a pointer to the right place.
- Cost/speed vs quality trade-off is real: rules are free and instant but brittle; the LLM is ~1.2 s and ~$0.0016 but handles typos, ambiguity and gaps.

**Next:** Day 5: Streamlit app showing answer, path, latency and cost. Ideas to revisit: narrower rules (specific question intents, not broad topic words), an "answer useful?" column judged by hand.

## Week 1 Day 5 (Sat Oct 10): Streamlit app for the FAQ Agent

**Learn:** Streamlit basics (Basic concepts docs). Check questions: 2.5 / 3.
- Streamlit reruns the whole script on every interaction (every click, not every visit). Uncached setup (loading rules/policy, creating the API client) would repeat on every click: slow and wasteful, though not an API cost — only sending a question costs money. Fix: `@st.cache_resource`. `st.session_state` keeps history across reruns.
- One shared `route()` function: one place to fix, the app and the eval script can't drift, and every eval run tests the exact code users hit.
- Cost, latency and path are operator metrics (verify routing, tune rules, track cost vs budget). End users need the answer, its source, an AI-generated note, a 👍/👎 and an escalation path.

**Build:**
- Installed Streamlit; `requirements.txt` updated with `Set-Content -Encoding ascii`.
- Refactored `day04/router.py`: extracted `route(question, rules, policy, client)` plus loader functions; `main()` uses it.
- **Regression test** after the refactor: reran all 26 questions. Same 20 rule / 6 LLM split, all 20 rule answers identical, rule precision 20/20. Only LLM latency changed — and faq-02's wording (55 → 75 output tokens) even at temperature 0.
- `day05/app.py`: ask a question or pick an example; shows answer, ⚡ Rule / 🤖 AI badge, matched categories, latency, tokens, cost; session history with running totals; sidebar toggles "Send everything to AI (rules off)" and "Show operator details". Run: `streamlit run day05\app.py`.

**Numbers, rules on vs off:**

| Question | Rules on | Rules off (all AI) |
|---|---|---|
| When does the CAB meet? | 0 ms, $0 | 1,201 ms, $0.001571 (1,271 in / 60 out) |
| SIM template refresh: pre-approved or normal? | 0 ms, $0 | 1,237 ms, $0.001573 (1,283 in / 58 out) |

- AI cost is ~$0.0016 per answer whatever the question, because ~1,270 of the input tokens are the policy sent with every call. Forecast = questions reaching the AI × ~$0.0016. At 10,000/day for one question: ~$16/day (~$470/month) vs $0. Prompt caching would cut the policy cost.

**Live testing with new questions of my own** (rules on):
- faq-22 → AI and hd-05 → Rule, as on Day 4.
- "what is daily cab meeting time?" → Rule, cab_approval ✓ (answer corrects the premise: weekly, Wednesday).
- "outage… fix tested… deploy tonight, which change type?" → Rule, emergency_change ✓.
- "what all details needed when i am submitting a standard change?" → Rule, **lead_time_scheduling ✗** (should be documentation_templates). Caused by the `when … submit` pattern Claude Code added on Day 4 to pass faq-26: a rule tuned to one test question misfired on a new one — instant, free and confidently wrong.
- "deployment steps and resources for an approved change?" → AI, no match, 2,146 ms, $0.001854.

**What broke:**
- Turning "Show operator details" off also hid the example-questions dropdown: Claude Code put it inside the operator section — a product decision I didn't ask for. Examples help end users too, so they belong in both views. Fix: move the dropdown out of `if operator:`.

**What I learned:**
- Even at temperature 0 the LLM isn't byte-for-byte repeatable; regression checks should assert on path, category and key facts, not exact wording.
- AI coding tools fill gaps with their own product guesses: review the plan and test the result.
- Tuned keyword rules keep misfiring on unseen phrasing; the router needs narrower, intent-level rules or fewer rules.

**Next:** Day 6 (Sun Oct 11): README with results table and Mermaid architecture diagram; Week 1 check-in.

## Week 1 Session 6 (Sun Oct 11): Measuring the FAQ Agent, README

**Plan change:** interview calls will take whole days, so the plan now counts numbered sessions instead of dated days. 51 sessions, target finish **Dec 6** (no scope cut; free days can hold two sessions). Check-ins after every 7th session. Next session: "Start Session 7".

**Learn:** Measuring AI features: accuracy, latency, cost per answer ("Define success criteria and build evaluations", Claude docs). Check questions: 2.25 / 3.
- Q1 Forecasting: budget on the holdout rate (rules answer 36-38%, ~$300/month at 10,000 questions/day), with the seen rate (77%, ~$110/month) as a best case that has to be earned by promoting frequent, stable questions to rules. The 77% is inflated because the rules were tuned on those questions.
- Q2 Latency: the average is for internal tracking; the SLA goes on the percentile (p95), per path, with headroom (e.g. "95% of AI answers within 2.5 s"). Same idea as "95% of P1 incidents resolved within 4 hours": the average hides the users who waited.
- Q3 Fixing the misfiring rule: measure first (baseline), then fix, move the misfired question into the regression set, and judge the fix on fresh holdout questions. Fixing before the eval loses the "before" picture.

**Build:**
- Wrote 6 more holdout questions myself (hd-09 to hd-14) → 14 unseen questions. Note: these are new questions, not the 5 Day 5 live questions, so the `when ... submit` misfire question is still not in the holdout.
- `day06/eval.py`: runs `route()` on all 40 questions (26 seen + 14 holdout) in two modes, `router` and `all_llm`; confirms the number of calls and cost first. Writes `results.csv` (80 rows).
- Hand-graded usefulness (Y / P / N) for all 28 holdout rows and 40 of 52 seen rows (faq-10 to faq-15 still ungraded).
- `day06/summarize.py` → `summary.md`: per mode x set: rule share, rule precision, useful rate, avg and p95 latency per path, cost per answer, blended cost per question, projection per 10,000.
- Root `README.md` for Project 1: problem, Mermaid diagram, headline table, full results, findings, "When should you use rules instead of an LLM?", next steps, how to run, known issues.

**Numbers (holdout, 14 new questions):**

| | Router | All-LLM |
|---|---|---|
| Answered by rules | 36% (5/14) | 0% |
| Useful answers | 57% | 89% |
| Cost per question | $0.00107 | $0.00168 |
| Cost per useful answer | $0.00188 | $0.00188 |
| p95 latency, LLM answers | 1,696 ms | 1,735 ms |

- Rule answers on the holdout: right category 4/5, but useful only 10% (hd-02 P; hd-05, hd-08, hd-11, hd-13 N). For each of the 4 N's the LLM gave a useful answer.
- Seen set: rules answered 77% (20/20 right category) but rule answers were 68% useful vs 100% for the LLM (graded rows).
- Out-of-scope rules (payroll, password) were the only clear rule win: 2/2 useful, $0, 0 ms.
- Total eval cost about $0.09.

**What I learned:**
- Cost per useful answer is the metric that matters. The router's 36% saving on cost per question disappears once only useful answers count: it saved money by giving unhelpful answers for free.
- Rules fit narrow intents with one fixed answer, not broad topics.
- hd-11 was a second keyword misfire: it matched only the phrase `change request`.
- Grounding mostly held; two minor slips: faq-16 (claims all mandatory fields are on the Plan tab) and hd-12 ("the policy document above" refers to the hidden system prompt).
- At temperature 0 every LLM question got identical text in both modes, so a response cache for repeated questions is a cheaper, higher-quality "rule" than keyword matching.
- My grading rubric: an honest "the policy doesn't cover this" is useful only if it points the user somewhere (hd-01, hd-09 = Y; hd-03 = N).

**What broke / fixed:**
- First README draft attributed the `when ... submit` misfire to hd-11 and claimed "0 hallucinations"; corrected both against the data.
- Cleanup: an empty `day04/hideout.json` (typo) and a duplicate Excel export, removed before committing.

**Next:** Week 1 check-in. Then Session 7: RAG head start (synthetic runbooks). Carry-overs: grade faq-10 to faq-15; before/after test of the rule fixes on fresh holdout questions.
