# LangPacks Package

Owns the structure for language learning content and language packs.

## Language Pack Format

Language packs are JSON documents that describe learning content for one target language. The canonical machine-readable contract lives in `schema/language-pack.schema.json`.

Each pack is organized as:

1. Pack metadata: `schema_version`, `pack_id`, and target `language`.
2. Levels: CEFR-aligned groups from `A1` through `C2`.
3. Topics: thematic groups inside a level, such as greetings or travel.
4. Lessons: ordered units inside a topic.
5. Exercises: practice items inside a lesson.
6. Answers and explanations: accepted answers and learner-facing feedback for every exercise.

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
- `language`: Target language metadata.
- `levels`: One or more proficiency levels with topics and lessons.

Language metadata includes:

- `code`: BCP 47 language code, for example `es` or `pt-BR`.
- `name`: English display name.
- `native_name`: Native display name.
- `direction`: Text direction, either `ltr` or `rtl`.

## Content Rules

- IDs are stable, lowercase slugs and should not be reused for different content.
- `order` is zero-based within each sibling list.
- Lessons must include at least one exercise.
- Exercises must include at least one accepted answer and one explanation.
- Multiple-choice exercises should include `options`; the accepted answer value should reference the correct option ID.
- Free-text and translation exercises should put accepted learner responses in `answers[].value`; `normalized_value` can be supplied for matching.

Supported exercise types are:

- `flashcard`
- `multiple_choice`
- `text_input`
- `translation`
- `listening`
- `ordering`

## Example

See `examples/es-a1-greetings.json` for a minimal Spanish A1 pack.

## Verification

The repository does not currently include a JSON Schema validator dependency. Use the standard library to confirm example files are valid JSON:

```sh
python -m json.tool packages/lang-packs/examples/es-a1-greetings.json >/dev/null
```
