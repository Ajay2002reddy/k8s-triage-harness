# Kickoff prompt

Paste into a new Claude Code session opened in this repo (locally: run `claude` in the repo root).

---

Read `CLAUDE.md`, `docs/PROJECT_BRIEF.md` and `PROGRESS.md`. Work only on the milestone(s) under **Next** in `PROGRESS.md`.

1. Before coding, check the environment (Docker, kind, kubectl, uv, python3) and say which path you'll use: local kind, or CI-only with fixtures.
2. Write ADR-001 (architecture) with the `write-adr` skill.
3. Build with tests first for harness logic.
4. Before opening the PR, run the `harness-reviewer` subagent on the diff.
5. Finish with the `milestone-close` skill.

Report in bullets: what runs ([Verified]/[Unverified]), CI link, decisions I need to make, plan for the next milestone. Stop at the milestone boundary.
