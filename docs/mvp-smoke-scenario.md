# MVP Smoke Scenario

This smoke scenario covers the Stage 1 learner path across the current
Telegram-first MVP surface and API contract:

1. Start the local project.
1. Register a learner.
1. Start and complete a lesson.
1. Submit at least one incorrect answer.
1. Repeat or review the mistake.
1. View learner progress.

## Preconditions

- Local environment values are copied from `.env.example` to `.env`.
- PostgreSQL and the API are running with migrations applied.
- At least one published lesson exists in the API database with one or more
  exercises and answer keys.
- For the Telegram path, `TELEGRAM_BOT_TOKEN` is set.

Start the local stack from the repository root:

```shell
docker compose up db api
```

When testing the Telegram flow as well, run the full stack:

```shell
docker compose up
```

## API Smoke Path

Use the API path when validating the backend contract without Telegram:

1. Confirm the API is ready.

   ```shell
   curl http://localhost:8000/health
   ```

   Expected result: HTTP `200` with `"status": "ok"`.

1. Register or update a learner.

   ```shell
   curl -s -X POST http://localhost:8000/learning/users \
     -H 'Content-Type: application/json' \
     -d '{"telegram_id":1001,"username":"mvp_smoke","first_name":"MVP","interface_language":"en"}'
   ```

   Expected result: HTTP `201` with a learner `id`. Save this value as
   `USER_ID`.

1. List published lessons.

   ```shell
   curl -s http://localhost:8000/learning/lessons
   ```

   Expected result: HTTP `200` with at least one lesson where
   `exercise_count` is greater than `0`. Save the lesson `id` as `LESSON_ID`.

1. Start the lesson.

   ```shell
   curl -s -X POST http://localhost:8000/learning/sessions \
     -H 'Content-Type: application/json' \
     -d '{"user_id":"'"$USER_ID"'","lesson_id":"'"$LESSON_ID"'"}'
   ```

   Expected result: HTTP `201` with `status` set to `in_progress`. Save
   `session_id` as `SESSION_ID`.

1. Fetch the current exercise.

   ```shell
   curl -s http://localhost:8000/learning/sessions/"$SESSION_ID"/exercise
   ```

   Expected result: HTTP `200` with an `exercise` object containing the prompt
   and payload shown to the learner.

1. Submit an intentionally incorrect answer.

   ```shell
   curl -s -X POST http://localhost:8000/learning/sessions/"$SESSION_ID"/answers \
     -H 'Content-Type: application/json' \
     -d '{"answer":"__incorrect_smoke_answer__"}'
   ```

   Expected result: HTTP `200` with `is_correct` set to `false` when the
   exercise has accepted answers configured. The returned progress advances by
   one exercise.

1. Continue submitting answers until `session_completed` is `true`.

   Expected result: the final answer response includes progress with `status`
   set to `completed`.

1. View detailed progress.

   ```shell
   curl -s http://localhost:8000/learning/users/"$USER_ID"/progress
   ```

   Expected result: HTTP `200` with the completed lesson progress entry.

1. View aggregate progress.

   ```shell
   curl -s http://localhost:8000/learning/users/"$USER_ID"/progress/stats
   ```

   Expected result: HTTP `200` with `answer_count` greater than `0`,
   non-empty `last_activity_at`, and accuracy fields reflecting the submitted
   answers.

1. View missed-exercise review.

   ```shell
   curl -s http://localhost:8000/learning/users/"$USER_ID"/review
   ```

   Expected result: HTTP `200` with a `cards` list containing the intentionally
   missed exercise until a later correct attempt clears it.

## Telegram Smoke Path

Use the Telegram path when validating the learner-facing MVP:

1. Send `/start` to the bot.
1. List lessons with `/lessons`.
1. Select or start a lesson with `/lesson <lesson-slug-or-id>`.
1. Answer one exercise incorrectly.
1. Finish the lesson.
1. Send `/review`, `/mistakes`, or `/repeat_errors`.
1. Send `/progress`.

Expected result: the bot lists available lessons, advances through the lesson,
shows incorrect-answer feedback, exposes a repeat/review queue for mistakes,
and returns aggregate learner progress.

## Automated Coverage

The scaffold includes an API MVP contract test that verifies the route sequence
needed by this scenario is exposed in the OpenAPI schema:

```shell
pytest services/api/tests/test_mvp_contract.py
```

CI also runs a PostgreSQL-backed API integration test for this learner path.
Use this manual smoke scenario when validating the Telegram bot or local
end-to-end behavior outside automated API coverage.
