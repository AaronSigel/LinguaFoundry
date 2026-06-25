# Core Package

Owns SRS and domain logic for LinguaFoundry.

## Learning Sessions

`linguafoundry_core.learning` provides the Telegram-independent lesson flow:

- start a lesson with `LearningSessionManager.start_lesson`
- fetch the current exercise with `get_current_exercise`
- submit and check an answer with `submit_answer`
- finish a lesson with `complete_lesson`

Incorrect answers create lightweight review items in the manager's review store.
Use `get_due_review_items` when callers need scheduling metadata, or
`get_due_review_exercises` when callers only need exercises ready for repeat
practice. Callers can run due items through a separate review workflow with
`start_review_session`, `get_current_review_exercise`, and
`submit_review_answer`. Review answers advance the review session and recalculate
the item's next `due_at` timestamp. Review dates are calculated by
`calculate_review_due_at` with simple 1, 3, 7, and 14 day intervals.

The initial implementation uses plain dataclasses and an in-memory store so
service layers can adapt it to bot, API, or durable persistence concerns later.

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
- `CompletionStatus`

## Verification

Run the focused core tests from the repository root:

```sh
pytest tests/core packages/core/tests
```
