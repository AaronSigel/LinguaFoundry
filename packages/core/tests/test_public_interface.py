from datetime import datetime, timedelta, timezone

import linguafoundry_core
from linguafoundry_core import models
from linguafoundry_core.answers import check_answer
from linguafoundry_core.learning import LearningSessionManager
from linguafoundry_core.review import build_mistake_review_queue
from linguafoundry_core.review_schedule import calculate_review_due_at


def test_package_root_exposes_production_models_and_shared_helpers() -> None:
    reviewed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert linguafoundry_core.Lesson is models.Lesson
    assert linguafoundry_core.Exercise is models.Exercise
    assert linguafoundry_core.check_answer is check_answer
    assert linguafoundry_core.calculate_review_due_at is calculate_review_due_at
    assert linguafoundry_core.check_answer(" HOLA ", {"answer": "hola"}) is True
    assert linguafoundry_core.calculate_review_due_at(reviewed_at) == (
        reviewed_at + timedelta(days=1)
    )


def test_package_root_does_not_export_legacy_prototype_workflows() -> None:
    legacy_names = (
        "AnswerResult",
        "InMemoryLearningSessionStore",
        "InMemoryReviewSessionStore",
        "InMemoryReviewStore",
        "LearningSessionManager",
        "ReviewAnswerResult",
        "ReviewCard",
        "ReviewItem",
        "ReviewSessionState",
        "SessionState",
        "SessionStatus",
        "build_mistake_review_queue",
    )

    for name in legacy_names:
        assert name not in linguafoundry_core.__all__
        assert not hasattr(linguafoundry_core, name)

    assert LearningSessionManager.__module__ == "linguafoundry_core.learning"
    assert build_mistake_review_queue.__module__ == "linguafoundry_core.review"
