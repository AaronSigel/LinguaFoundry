# Core Package

Owns SRS and domain logic for LinguaFoundry.

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
- `CompletionStatus`

## Verification

Run the focused core tests from the repository root:

```sh
pytest tests/core
```
