# Development Process

LinguaFoundry uses small, reviewable changes that can be implemented by humans or coding agents.

## Issue Intake

Each work item should include:

- A short summary of the user or engineering outcome.
- Scope boundaries and acceptance criteria.
- Relevant component ownership, links, and constraints.
- Any required ADR updates.

## Coding Agent Workflow

When a coding agent implements a task, it should:

1. Inspect the repository layout, existing conventions, configuration, and nearby files before editing.
1. Keep changes scoped to the approved task and avoid unrelated refactors.
1. Preserve existing public interfaces unless the task explicitly changes them.
1. Add or update tests and documentation in proportion to the risk of the change.
1. Run the repository's relevant verification commands when available.
1. Report changed files, verification results, and known risks for human review.

## Human Review

Human reviewers should check that the implementation matches the issue, follows local conventions, has suitable verification, and does not introduce hidden scope changes.

## Decision Records

Use ADRs for decisions that are hard to reverse or likely to guide future work. Store them in `docs/adr/` using the local template.
