# Core Package

Owns SRS and domain logic for LinguaFoundry.

## Learning Sessions

`linguafoundry_core.learning` provides the Telegram-independent lesson flow:

- start a lesson with `LearningSessionManager.start_lesson`
- fetch the current exercise with `get_current_exercise`
- submit and check an answer with `submit_answer`
- finish a lesson with `complete_lesson`

The initial implementation uses plain dataclasses and an in-memory store so
service layers can adapt it to bot, API, or durable persistence concerns later.

## Verification

From the repository root:

```bash
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
- `UserProgressStats`
- `calculate_user_progress_stats`
- `CompletionStatus`

## Verification

Run the focused core tests from the repository root:

```sh
pytest tests/core
```
