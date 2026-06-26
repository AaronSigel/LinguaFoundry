from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_published_language_pack_update_policy_documents_safe_versioning() -> None:
    readme = REPOSITORY_ROOT / "packages" / "lang-packs" / "README.md"

    policy = " ".join(readme.read_text(encoding="utf-8").split())

    assert "## Published Pack Update Policy" in policy
    assert (
        "Learner progress, attempts, review state, and active sessions are tied "
        "to the imported lesson record for the `pack_id` and `content_version`"
    ) in policy
    assert "Keep `pack_id` stable for the same product or curriculum line" in policy
    assert (
        "Increment `content_version` for any learner-visible lesson, exercise, "
        "answer, explanation, ordering, or metadata change"
    ) in policy
    assert (
        "Keep level, topic, lesson, and exercise IDs stable when the item "
        "represents the same learning content"
    ) in policy
    assert "Do not reuse a removed ID" in policy
    assert (
        "Do not edit a previously published `content_version` in place, except "
        "for unreleased local corrections before import"
    ) in policy
    assert (
        "Remove or replace content only by publishing a new `content_version`" in policy
    )
    assert (
        "the old version must remain available until all active sessions and "
        "historical progress can safely reference it"
    ) in policy
    assert (
        "preserving user history on earlier versions while allowing updated content "
        "to be published"
    ) in policy
