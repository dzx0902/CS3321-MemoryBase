# MemoryBase Agent Guide

## Default Contract

- 中文回复；code, comments, commit messages in English.
- Deliver requested changes end-to-end: inspect current state, implement or review, verify, and report evidence.
- Do not skip user-named requirements. If blocked, report the blocker, evidence, and remaining risk.
- Treat existing user changes as intentional. Do not revert unrelated work.

## Progressive Disclosure

- This file is the always-loaded repo guide. Keep it short and operational.
- Detailed personal execution planning lives in `docs/prompt.md` when present. It is ignored by git and should be read only when executing the project owner's personal workflow.
- Formal project sources are `README.md`, `CONTRIBUTING.md`, `docs/00-14`, `database/*.sql`, and `.github/issues.yaml`.
- Formal sources are inputs to review, not unquestioned truth. Design docs, SQL, and issue bodies can drift; compare them before using any one source as authoritative.

## Issue Workflow

- Before starting work, check live GitHub issue state with `gh issue view/list`; do not rely only on local issue IDs.
- Confirm assignment before work starts; ask the owner before adding or changing assignees.
- Personal owner branch is `jflin`, based on latest `dev`; PRs go from `jflin` to `dev`. `main` is updated only by integration PRs.
- Default to one issue at a time, but time-boxed phase work may batch several related issues into one PR.
- Even in a batched PR, keep one reviewable change per issue, validate each issue separately, and prepare evidence for each GitHub issue before moving on.
- Use `Refs #<number>` for PRs to `dev`; include every issue number in batched PR bodies. Close issues only after the agreed integration/closure step.

## Approval Boundary

- Default workflow is local edit plus validation plus diff summary, then stop for owner review.
- Do not run `git commit`, `git push`, `gh pr create`, `gh pr edit`, `gh pr merge`, `gh issue edit`, `gh issue comment`, or `gh issue close` unless the project owner explicitly requests that exact remote or git action in the current context.
- Even when the owner authorizes continued implementation, stop before commit/push/PR/merge and wait for an explicit post-review confirmation for that landing step. Treat implementation approval and landing approval as separate gates.
- When the owner approves landing for a PR, that approval does not extend to starting the next PR. Wait for fresh implementation-start authorization before opening any follow-up branch or PR.
- Words such as "continue", "fix", "implement", "proceed", or "按照流程" do not authorize commit, push, PR mutation, issue mutation, merge, or close.
- If the owner says "commit", only create the local commit after showing validation evidence or using already reviewed evidence.
- If the owner says "push", only push already-reviewed local commits to the requested branch; do not bundle new edits into that push.
- After local implementation, provide changed files, validation commands, residual risks, and a suggested commit message instead of committing automatically.

## GitHub Comments

- For multi-line `gh issue comment` or PR comments, use heredoc or another real-newline input method.
- Do not put literal `\n` inside ordinary quoted `--body` strings.
- After posting a multi-line comment, fetch it back and verify the Markdown source:

```bash
gh issue view <number> --repo dzx0902/CS3321-MemoryBase --json comments --jq '.comments[-1].body'
```

## Database Work

- Schema issues are often review/alignment tasks, not from-scratch rewrites.
- Compare SQL against `.github/issues.yaml`, logical design, data dictionary, and ER docs before editing.
- If SQL, docs, or issue acceptance criteria disagree on table names, fields, enums, constraints, trigger behavior, or API contracts, stop and ask the project owner which source to align to.
- Validate PostgreSQL SQL with executable evidence when possible, preferably on a temporary database.
