# Core Package

Owns shared domain entities and helper logic for LinguaFoundry.

## Production Shared Helpers

The production path is `Bot -> API -> PostgreSQL`. The bot talks to the API;
the API owns durable learning-session, progress, attempt, and review-state
updates in PostgreSQL.

The core package exposes only shared entities and stateless helpers needed by
that path:

- `linguafoundry_core.answers` for answer extraction, display, normalization,
  and scoring.
- `linguafoundry_core.review_schedule` for lightweight review due-date
  calculation.
- `linguafoundry_core.models` for framework-independent domain entities.

## Legacy Prototype Modules

`linguafoundry_core.learning` and `linguafoundry_core.review` contain earlier
in-memory lesson and mistake-review workflows. They are intentionally not
exported from the package root because they are outside the production
Bot -> API -> PostgreSQL path. Tests that cover those prototypes import the
modules directly.

## Verification

From the repository root:

```sh
PYTHONPATH=packages/core pytest packages/core/tests
```

## Public Interface

The `linguafoundry_core` package exposes the base learning domain model:

- `User`
- `Language`
- `CEFRLevel`
- `Lesson`
- `Exercise`
- `Attempt`
- `LearningSession`
- `Progress`
- `ReviewState`
- `ReviewStatus`
- `UserProgressStats`
- `calculate_user_progress_stats`
- `calculate_review_due_at`
- `check_answer`
- `extract_accepted_answers`
- `expected_answer_text`
- `normalize_answer`
- `CompletionStatus`

## Verification

Run the focused core tests from the repository root:

```sh
pytest tests/core packages/core/tests
```
