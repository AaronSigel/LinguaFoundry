# Pull Request Rules

These rules keep LinguaFoundry changes reviewable and traceable.

## Required

- Keep each pull request focused on one issue or one coherent change.
- Link the related issue, task, or ADR in the pull request description.
- Fill in the pull request template before requesting review.
- Include verification details for tests, linters, manual checks, or explain why
  verification was not run.
- Update documentation when behavior, architecture, workflow, or public
  interfaces change.
- Add or update an ADR in `docs/adr/` for decisions that affect architecture,
  data ownership, integration boundaries, or long-term operating model.

## Review Expectations

- Review for correctness, maintainability, security, test coverage, and user
  impact.
- Resolve review comments with code changes or a clear written decision.
- Do not merge while required checks are failing.
- Do not merge unrelated refactors with feature or bug-fix work.
- Prefer small follow-up issues over expanding pull request scope during review.

## Merge Readiness

A pull request is ready to merge when it has a completed template, linked
context, passing required checks, resolved review threads, and documented
residual risks.
