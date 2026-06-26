# LangPacks Package

Owns the structure for language learning content and language packs.

## Language Pack Format

Language packs are JSON documents that describe learning content for one target
language. The canonical machine-readable contract lives in
`schema/language-pack.schema.json`.

Each pack is organized as:

1. Pack metadata: `schema_version`, `pack_id`, `content_version`, and target
   `language`.
1. Levels: CEFR-aligned groups from `A1` through `C2`.
1. Topics: thematic groups inside a level, such as greetings or travel.
1. Lessons: ordered units inside a topic.
1. Exercises: practice items inside a lesson.
1. Answers and explanations: accepted answers and learner-facing feedback for
   every exercise.

```text
language pack
`-- levels[]
    `-- topics[]
        `-- lessons[]
            `-- exercises[]
                |-- answers[]
                `-- explanation
```

## Required Top-Level Fields

- `schema_version`: Format version. Use `1.0`.
- `pack_id`: Stable lowercase identifier, for example `es-core-a1`.
- `content_version`: Version of the pack content. Increment it when lesson or
  exercise content changes.
- `language`: Target language metadata.
- `levels`: One or more proficiency levels with topics and lessons.

Language metadata includes:

- `code`: BCP 47 language code, for example `es` or `pt-BR`.
- `name`: English display name.
- `native_name`: Native display name.
- `direction`: Text direction, either `ltr` or `rtl`.

## Content Rules

- IDs are stable, lowercase slugs and should not be reused for different
  content.
- `order` is zero-based within each sibling list.
- Lessons must include at least one exercise.
- Exercises must include at least one accepted answer and one explanation.
- Multiple-choice exercises should include `options`; the accepted answer value
  should reference the correct option ID.
- Free-text and translation exercises should put accepted learner responses in
  `answers[].value`; `normalized_value` can be supplied for matching.

## Published Pack Update Policy

Published language packs are append-only by content identity. Learner progress,
attempts, review state, and active sessions are tied to the imported lesson
record for the `pack_id` and `content_version` that the learner used.

Use this policy when updating a pack that has already been imported or released:

- Keep `pack_id` stable for the same product or curriculum line.
- Increment `content_version` for any learner-visible lesson, exercise, answer,
  explanation, ordering, or metadata change.
- Keep level, topic, lesson, and exercise IDs stable when the item represents
  the same learning content. This lets the importer create a new versioned copy
  without breaking historical references.
- Do not reuse a removed ID for different content in a later version. Create a
  new slug instead.
- Do not edit a previously published `content_version` in place, except for
  unreleased local corrections before import. Re-importing the same
  `content_version` updates that version's rows and can change what learners on
  that version see.
- Remove or replace content only by publishing a new `content_version`; the old
  version must remain available until all active sessions and historical
  progress can safely reference it.

The importer stores each lesson under `pack_id`, `content_version`, and the
stable lesson slug. This creates distinct database records for new content
versions, preserving user history on earlier versions while allowing updated
content to be published.

Supported exercise types are:

- `flashcard`
- `multiple_choice`
- `text_input`
- `translation`
- `listening`
- `ordering`

## Example

Available example packs:

- `examples/es-a1-greetings.json`: minimal Spanish A1 greetings pack.
- `examples/fr-a1-seed.json`: minimal French A1 seed pack with several
  lessons for manual learning-flow testing.

## Verification

Validate all example packs against the JSON Schema contract with:

```shell
python -m services.api.app.lang_packs --check packages/lang-packs/examples
```

`pytest services/api/tests/test_lang_packs.py` also validates the committed
example packs in CI.

## Importing

Import packs into PostgreSQL after API migrations have run:

```shell
python -m services.api.app.lang_packs packages/lang-packs/examples
```

The importer is idempotent. It stores `content_version` as the language pack
version used by learning sessions, updates lessons by pack ID plus content
version plus stable lesson slug, and updates exercises by stable lesson plus
exercise slug. Stable lesson slugs are built from `pack_id`, level ID, topic ID,
and lesson ID. Exercise payloads include a globally stable exercise ID derived
from the stable lesson slug plus exercise ID.
