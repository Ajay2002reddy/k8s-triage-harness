---
name: write-adr
description: Write an Architecture Decision Record in docs/adr/ before making a real design choice (framework, provider, sandbox method, eval metric, taxonomy change, storage, tracing backend). Use whenever choosing between two or more viable options or changing the project brief.
---

# Write an ADR

A decision without an ADR can't be defended in an interview. Write it **before** the code.

## Steps
1. Next number: `ls docs/adr/` and take the highest NNN + 1. `000` is the template.
2. Copy `docs/adr/000-template.md` to `docs/adr/NNN-<kebab-title>.md`.
3. Fill in:
   - **Context**: the forcing problem plus the constraints from `docs/PROJECT_BRIEF.md` that apply.
   - **Options**: at least 2 real options. "Do nothing" counts if it's viable.
   - **Decision**: one sentence.
   - **Consequences**: what gets easier, what gets harder, and **the signal that would prove it wrong**.
4. Keep it under 60 lines. Link to sources (docs, issues) for factual claims.
5. If it changes scope or constraints, also edit `docs/PROJECT_BRIEF.md` and reference the ADR.
6. Set status to `proposed`. The owner flips it to `accepted` when reviewing the PR.

## Decisions that always need an ADR
- Agent framework or none (plain loop vs LangGraph/Pydantic AI)
- LLM provider abstraction
- Sandbox approach (RBAC-only vs gVisor vs separate pod)
- Root-cause taxonomy changes
- Eval metric definitions and the CI gate threshold
- Tracing backend (Langfuse vs Grafana/Tempo)
