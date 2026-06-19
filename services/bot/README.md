# Bot Service

Telegram-facing entrypoint for the Stage 1 MVP.

## Review Command

`services.bot.review` provides framework-agnostic handlers for the Telegram
mistake review command. `/review`, `/mistakes`, and `/repeat_errors` render the
learner's SRS-lite queue from `linguafoundry_core.review`.

## Verification

From the repository root:

```sh
pytest services/bot/tests packages/core/tests/test_review.py
```
