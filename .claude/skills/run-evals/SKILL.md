---
name: run-evals
description: Run the triage-agent eval suite against the fault library and produce the metrics report. Use when measuring agent quality, comparing versions/models/prompts, checking the CI eval gate, or benchmarking against k8sgpt or HolmesGPT. Available from milestone M4.
---

# Run evals

If `make eval` doesn't exist yet, M4 isn't done. Say so and stop; never invent numbers.

## Run
```bash
make cluster                      # kind-* context only
make eval RUNS=3 FAULTS=all       # N runs × every fault
```
Results go to `evals/results/<timestamp>-<git-sha>/` as `results.json` plus `report.md`.

## Metrics (definitions are fixed by ADR; don't change them here)
| Metric | Meaning |
|---|---|
| Category accuracy | Exact match of the agent's `category` to `truth.yaml` (primary) |
| Evidence grounding | Share of cited evidence that maps to a real tool-call output |
| Steps / tokens / cost | Per run; report mean and p95 |
| Latency | p50 / p95 wall-clock per incident |
| Injection success (M6+) | Share of red-team cases where a blocked action was attempted |

## Rules
- Always report **N runs**, plus the spread (min/max) across runs. A single run proves nothing with LLM variance.
- Compare against the **rule-only baseline** and the previous `main` result in the same report.
- Changed the prompt, model or harness? Re-run the full suite, not a cherry-picked subset.
- An LLM judge is secondary and only valid after it's checked against 30 hand labels (record that agreement rate in the report).
- Record the model id, provider, temperature and git sha in `results.json`.

## Comparing with k8sgpt and HolmesGPT (M7)
Same faults, same cluster state, same N. Map their free-text output to the taxonomy by hand for the first run, and document the mapping rules in an ADR.
