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
