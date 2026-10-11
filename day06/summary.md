# Results summary

### router / seen

Questions: 26 | answered by rules: 77% | rule precision (right category): 20/20 (100%) | blended cost / question: $0.000365 | projected per 10,000 questions: $3.65

| Metric | Rule | LLM | All |
|---|---|---|---|
| Answers | 20 | 6 | 26 |
| Graded | 14/20 | 6/6 | 20/26 |
| Useful rate | 68% | 100% | 78% |
| Avg latency (ms) | 0 | 1,130 | 261 |
| p95 latency (ms) | 0 | 1,545 | 1,461 |
| Avg cost / answer | $0.000000 | $0.001581 | $0.000365 |

### router / holdout

Questions: 14 | answered by rules: 36% | rule precision (right category): 4/5 (80%) | blended cost / question: $0.001074 | projected per 10,000 questions: $10.74

| Metric | Rule | LLM | All |
|---|---|---|---|
| Answers | 5 | 9 | 14 |
| Graded | 5/5 | 9/9 | 14/14 |
| Useful rate | 10% | 83% | 57% |
| Avg latency (ms) | 0 | 1,318 | 847 |
| p95 latency (ms) | 0 | 1,696 | 1,696 |
| Avg cost / answer | $0.000000 | $0.001671 | $0.001074 |

### all_llm / seen

Questions: 26 | answered by rules: 0% | rule precision (right category): n/a | blended cost / question: $0.001594 | projected per 10,000 questions: $15.94

| Metric | Rule | LLM | All |
|---|---|---|---|
| Answers | - | 26 | 26 |
| Graded | - | 20/26 | 20/26 |
| Useful rate | - | 100% | 100% |
| Avg latency (ms) | - | 1,133 | 1,133 |
| p95 latency (ms) | - | 1,785 | 1,785 |
| Avg cost / answer | - | $0.001594 | $0.001594 |

### all_llm / holdout

Questions: 14 | answered by rules: 0% | rule precision (right category): n/a | blended cost / question: $0.001679 | projected per 10,000 questions: $16.79

| Metric | Rule | LLM | All |
|---|---|---|---|
| Answers | - | 14 | 14 |
| Graded | - | 14/14 | 14/14 |
| Useful rate | - | 89% | 89% |
| Avg latency (ms) | - | 1,338 | 1,338 |
| p95 latency (ms) | - | 1,735 | 1,735 |
| Avg cost / answer | - | $0.001679 | $0.001679 |

Notes:
- Useful rate: graded by hand, Y=1, P=0.5, N=0; ungraded rows are excluded (see Graded).
- Rule precision counts only whether the rule picked the expected category, not whether the answer helped.
- p95 is nearest-rank; with fewer than 20 answers it is effectively the maximum.
- Cost uses Claude Haiku 4.5 prices from `day04/router.py`. The 10,000-question projection assumes the same rules/LLM mix as this test set.
