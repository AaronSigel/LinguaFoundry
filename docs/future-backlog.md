# Future Backlog

This backlog records product and platform directions that are intentionally
outside the current Telegram-first MVP. Items here are not committed scope for
the baseline application; they exist to preserve direction and keep near-term
scaffold work focused.

## Future Directions

- LLM gateway: introduce a service boundary for model providers, prompt
  templates, safety controls, usage accounting, and fallback behavior.
- Agentic content pipeline: generate, review, validate, and publish lesson
  content through repeatable agent workflows with human approval gates.
- PDF ingestion: extract source text from PDFs, normalize it into reusable
  learning material, and keep provenance metadata for generated exercises.
- Web and mobile clients: add learner-facing clients beyond Telegram while
  preserving the API as the durable progress and session boundary.
- Expanded language packs: grow language-pack coverage, difficulty levels,
  localization metadata, and validation examples without coupling content to a
  specific client.

## Scoping Notes

- Keep the Stage 1 MVP centered on the Telegram bot, FastAPI backend,
  PostgreSQL persistence, shared core logic, and language-pack schema.
- Add ADRs before introducing hard-to-reverse architecture choices such as a
  production LLM provider contract, ingestion storage model, or multi-client
  authentication strategy.
- Update this backlog when future issues promote one of these directions into
  approved implementation scope.
