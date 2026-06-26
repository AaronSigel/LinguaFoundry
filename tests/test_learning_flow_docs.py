from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _normalized_doc(path: str) -> str:
    return " ".join((REPOSITORY_ROOT / path).read_text(encoding="utf-8").split())


def test_mvp_smoke_scenario_documents_resume_and_due_review_flow() -> None:
    smoke_scenario = _normalized_doc("docs/mvp-smoke-scenario.md")

    assert "Resume an in-progress lesson" in smoke_scenario
    assert "Repeat or review a due mistake" in smoke_scenario
    assert "Confirm the in-progress session can be resumed" in smoke_scenario
    assert '/learning/users/"$USER_ID"/sessions/active' in smoke_scenario
    assert (
        "Starting the same lesson again before completion should reuse that "
        "active session instead of creating a second cursor"
    ) in smoke_scenario
    assert "Newly missed exercises are tracked as active repetitions" in smoke_scenario
    assert (
        "review cards appear only when their `due_at` time has passed" in smoke_scenario
    )
    assert "`active_repetitions` is greater than `0`" in smoke_scenario
    assert (
        "UPDATE review_states SET due_at = now() - interval '1 minute'"
        in smoke_scenario
    )
    assert "prompt, expected answer text, and incorrect attempt count" in smoke_scenario
    assert "/review`, `/mistakes`, or `/repeat_errors" in smoke_scenario


def test_testing_guide_points_to_persisted_resume_and_review_coverage() -> None:
    testing_guide = _normalized_doc("docs/testing.md")

    assert "active-session resume and review-queue endpoints" in testing_guide
    assert "pytest services/api/tests/test_mvp_contract.py" in testing_guide
    assert (
        "verifies persisted attempts, progress, durable session state, resume "
        "behavior, and due-only review state after a new app instance is created"
    ) in testing_guide
    assert "TEST_DATABASE_URL=postgresql+asyncpg://" in testing_guide
    assert "pytest services/api/tests/test_mvp_integration.py" in testing_guide
    assert (
        "checking `/resume` against active durable sessions, or verifying due "
        "review cards outside the automated API integration path"
    ) in testing_guide
