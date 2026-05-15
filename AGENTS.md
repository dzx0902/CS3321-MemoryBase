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
- Confirm or add assignment before work starts.
- Personal owner branch is `jflin`, based on latest `dev`; PRs go from `jflin` to `dev`. `main` is updated only by integration PRs.
- Work one issue at a time. Finish validation before moving to the next issue.
- Use `Refs #<number>` for PRs to `dev`; close issues only after the agreed integration/closure step.

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
