---
name: milestone-close
description: End-of-session and end-of-milestone checklist. Updates PROGRESS.md and LEARNING.md, verifies CI, opens the milestone PR and writes the report. Use before ending any session, when a milestone is finished, or when the user says wrap up / stop / report.
---

# Close the session or milestone

Cloud sessions are short-lived. Anything not in the repo is lost, so this checklist is mandatory.

## 1. Verify, don't assume
- Run `make lint` and `make test` locally if possible, and record the result.
- Check the latest CI run for the branch (`gh run list --branch <branch> --limit 1`) and record the link and status.
- Tag every claim **[Verified: ran it]** or **[Unverified]**. Never write a CI status or number you didn't see.

## 2. Update `PROGRESS.md`
- Status table: state, "Verified in CI" (✅ with run link / ❌ / –), PR link.
- **Next**: the next milestone only, plus its first 3 concrete steps.
- **Verified** and **Unverified / assumptions**: move items between them honestly.
- **Open decisions (owner)**: anything that blocks the next milestone.
- **Log**: one dated line on what changed this session.

## 3. Update `LEARNING.md` (milestone close only)
Add 5 interview questions about what was built. Each answer is 2–4 lines and points to the file or ADR. Mix:
- 1 design question ("Why X over Y?" → ADR)
- 1 failure question ("What happens when … fails?")
- 1 security/safety question
- 1 trade-off question
- 1 "explain this code path" question

## 4. Commit and PR
- Commit with a clear message, then push the branch.
- Milestone close: open a PR to `main` titled `M<n>: <name>`. Body: what was built, how it was verified, open decisions, and a link to the LEARNING section.

## 5. Report to the owner (chat), as concise bullets
1. What runs, with [Verified]/[Unverified] tags
2. CI link and status
3. Decisions needed
4. Plan for the next milestone

Then **stop**. Don't start the next milestone without the owner's go-ahead.
