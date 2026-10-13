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

## Week 1 check-in (Sun Oct 11)

| Area | Score | Note |
|---|---|---|
| Build | 3 | FAQ Agent in Streamlit + rules-vs-LLM comparison, plus holdout, two-mode eval, shared `route()` with regression check |
| Understand | 2 | Check questions dipped mid-week (1.75/3, 1/3) and recovered (2.5/3, 2.25/3); can say when not to use rules |
| Measure | 3 | Before/after: prompt vs schema, router vs all-LLM, seen vs holdout; cost per useful answer |
| Communicate | 3 | README + diagram + results; 2-minute interview answer given in my own words (Oct 12, second attempt, with numbers added) |
| **Total** | **11 / 12** | Move on to Week 2 |

Quiz: 5 / 5. Mock interview: "When should a team use rules instead of an LLM?" First attempt (Oct 11) answered a different question (a to-do list for this project). Second attempt (Oct 12): principle + governance in my own words, then added my numbers and when rules fail (36% answered / 10% useful vs 89%; narrow single-answer intents only).

**Running scorecard:** Week 1: 11/12.

## Week 2 Session 7 (Mon Oct 12): What RAG is, runbook library

**Warm-up:** mock interview retried ("When should a team use rules instead of an LLM?"): own words plus my numbers → Week 1 Communicate 3, Week 1 total 11/12.

**Learn:** RAG basics ("Introducing Contextual Retrieval", Anthropic: longer-prompt note and RAG primer). Check questions: 2.25 / 3.
- Q1 Why not send all runbooks like the FAQ Agent: cost (~15,000 tokens ≈ $0.015/answer, ~10x) and latency, but mainly **accuracy** (the right step gets buried; overlapping and superseded runbooks get blended) and **scale**. When NOT to use RAG: small, stable knowledge bases (under ~200k tokens) can just be sent whole with prompt caching.
- Q2 Keyword rules fail two ways: **false match** (word trap: "freeze" = change freeze vs screens freezing) and **no match** (`\bfreezes?\b` doesn't match "freezing"; "unresponsive under high load" shares no words). Embeddings turn text into numbers that capture meaning, so similar meanings land close together with no shared words needed.
- Q3 A wrong RAG answer comes from **retrieval** (right chunk not in the top results) or **generation** (right chunks, wrong answer), plus a third case: **coverage gap** (no doc covers it; should say "I don't know"). Tell which by logging the retrieved chunks with every answer. (Slip: wrote "retrieval" where I meant "generation".)

**Repo change:** moved Project 1 into `change-request-faq-agent/` (dayNN kept as subfolders via `git mv`; `.env` path fixed in classify.py and router.py; project README moved there; root README is now a portfolio index). New projects get their own top-level folder.

**Build:**
- `runbook-assistant/data/`: 18 synthetic docs for the fictional operator "Northwind Mobile" (12 runbooks, 6 postmortems, 340-410 words each) + `INDEX.md`, generated with Claude Code in plan mode.
- Retrieval traps built in: different wording (RB-004 "unresponsive under high load"), overlapping pair (RB-004 CRM thread pool vs RB-006 API gateway breakers; PM-005 links both), superseded pair (RB-011 → RB-012, DNS), postmortem-only lessons, and no runbook for certificate expiry or replication lag (postmortems only).
- `runbook-assistant/design_notes.md`: answer key (facts and traps per doc). Never index it; don't read it before writing test questions.
- Domain review: edited RB-002 (billing batch); reviewed the other docs and found them realistic as written.
- `runbook-assistant/test_questions.md`: 7 questions written in real ticket language before any search exists, each with an expected doc: portal login "unable to authenticate" (RB-003), prepaid refill not processed (RB-005), expired certificate breaking quick payment (None), port-out past SLA (RB-007), MDN activation stuck in order management (RB-008), DNS lookups failing / which TTL (RB-012, superseded-pair test), "multiple applications responding very slowly" (overlap test).

**What I learned:**
- The domain expert's job in AI work: design the test data and its traps, and review AI-generated content for realism.
- Ticket-style questions are a better test than textbook questions. Q1 is a natural word trap: "authenticate" may pull RB-001 (HSS subscriber authentication), while the right answer is "no runbook covers portal login".

**Carry-overs to Session 8:** fix the overlap question's expected doc (RB-014 doesn't exist; RB-004 or RB-006); decide whether the certificate question should expect PM-004 (a postmortem covers it) rather than None; convert the questions to a clean file (id, question, expected doc) for scoring.

**Next:** Session 8: chunking, embeddings and ChromaDB; top-3 search for the test questions (index `data/` only).

## Week 2 Session 8 (Tue Oct 13): Chunking, embeddings and ChromaDB

**Learn:** Chroma "Getting Started" (create collection, add, query). Check questions: 1.75 / 3.
- Q1 Chunk by section: one section = one idea, so a clear embedding; fixed 200-word slices straddle sections and blur. Missed the second half: the `[doc_id | title | section]` label keeps near-identical sections apart (every runbook has an "Escalation" section) and tells the LLM what to cite.
- Q2 Superseded doc beating the current one: (1) metadata filter `superseded = false` at search time, (2) prompt rule "prefer newest, never use SUPERSEDED", and best of all (3) retire superseded docs from the index (document lifecycle, like retiring a CI). I had the right directions but not the mechanisms.
- Q3 Vector search always returns its top k, because "closest" ≠ "relevant". Checking for valid doc IDs can't detect this (every result has one); the fix is a distance cut-off calibrated on hit vs no-answer questions, plus an LLM "don't answer if the chunks don't cover it" rule.
- Habit to build: after each answer, ask "how exactly would this work in the code?"

**Environment issue:** `ingest.py` failed with "DLL load failed while importing rpds: An Application Control policy has blocked this file". Windows Smart App Control blocked a brand-new compiled dependency (`rpds-py` 2026.9.1); the other compiled parts (onnxruntime, tokenizers, Chroma's Rust bindings) loaded fine. Fix: `pip install --force-reinstall --no-deps "rpds-py==0.27.1"` (an older, widely downloaded build), pinned in requirements.txt. Lesson: security policies can block AI tooling on locked-down laptops; diagnose which file before changing anything.

**Build:**
- `pip install chromadb` (1.5.9); default embedding model all-MiniLM-L6-v2 (79 MB, local, free).
- `runbook-assistant/test_questions.json`: 7 questions with `expected_docs` (tq-01 and tq-03 decisions: tq-01 portal login = none; tq-03 expired certificate = PM-004).
- `runbook-assistant/ingest.py`: reads only `data/*.md` (never design_notes or test questions), front matter → metadata incl. `superseded`, one chunk per `##` section prefixed with `[doc_id | title | section]`, persistent collection `runbooks` in `chroma_db/` (git-ignored). Result: 18 docs → 116 chunks, avg 66 words (min 20, max 126).
- `runbook-assistant/search.py`: top-k with doc_id, section, distance, superseded flag; `--all` scores the test set (hit@k) and writes `search_results.csv`; `--k N`. No filtering, no LLM. **Cost: $0.**

**Numbers (raw search, k = 3):**

| id | expected | result |
|---|---|---|
| tq-01 | none | top distance 1.253 (RB-005, PM-003, RB-001) |
| tq-02 | RB-005 (+ RB-002 after review) | RB-002, RB-003, RB-009 |
| tq-03 | PM-004 | HIT (0.921) |
| tq-04 | RB-007 | HIT (1.165) |
| tq-05 | RB-008 | MISS: PM-003, RB-005, PM-003 |
| tq-06 | RB-012 | HIT: RB-012, RB-012, RB-011 (superseded 3rd) |
| tq-07 | RB-004 | HIT: RB-004, RB-012, RB-004 (RB-006 not in top 3) |

- **hit@3 = 4/6 (67%)** with the original labels; **5/6 (83%)** after relabeling tq-02 (same search results; `search_results.csv` is the pre-relabel run).
- tq-02 relabel decision (mine, as domain reviewer): a scheduled prepaid refill that didn't process could be the payment gateway (RB-005) or the billing batch (RB-002); both runbooks would help an on-call engineer, so both count. Logged both scores so the change is transparent.

**What I learned:**
- tq-05 missed because of vocabulary, not meaning: a typo ("activitaion") and US telecom jargon ("MDN") that RB-008 never uses ("activation queue", "provisioning"). Embeddings handle synonyms but not typos or company jargon; "stuck orders" pulled the payment docs instead. Possible fixes: LLM query rewriting (fix typos, expand jargon), a glossary/synonyms in the runbooks, a stronger embedding model.
- No clean "I don't know" cut-off yet: no-answer 1.253 vs misses 1.131-1.163 vs a hit at 1.165. Distance alone can't separate them, and 1 no-answer question is too few to calibrate.
- Top 3 can be all one doc (tq-03, tq-04): fine for answering (symptoms + fix), wasteful for finding the right doc. Fix: best chunk per doc, or k=5 then collapse.
- Superseded RB-011 still enters the top 3 (ranked 3rd) → metadata filter needed.
- "Applications responding slowly" (tq-07) is genuinely ambiguous (RB-004 vs RB-006 vs DNS); a good assistant may need to ask a clarifying question.

**Follow-up experiments (same session):**
- Rewrote tq-05 in plain words ("new phone number activation failing, orders stuck in provisioning"): **RB-008 ranked 1st at 0.944**, a stronger match than any original hit. Confirms the miss was vocabulary (typo + jargon), not missing content. (The rewrite fixed both at once, so typo vs jargon isn't separated.)
- `--k 5`: **hit@5 = 5/6**, the same as hit@3. tq-05 still misses; RB-008 isn't even in the top 5. Looking deeper doesn't fix a vocabulary miss; fixing the question (LLM query rewriting) or the content (glossary: MDN, orders) does.
- RB-008's tiny "Related docs" chunk (just a list of doc IDs) ranked 2nd for the rewritten question: the low-content-chunk problem. Candidate Week 3 experiment: drop or merge "Related docs" sections.
- `search_results.csv` now holds the relabeled `--k 5` run.

**Next:** Session 9: grounding and citations. Send the top chunks to Haiku and answer with `[source]` citations; add the superseded filter.
