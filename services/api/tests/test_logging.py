import json
import logging

from services.api.app.logging import configure_logging


def test_configure_logging_emits_structured_json(capsys) -> None:
    configure_logging("debug")
    logger = logging.getLogger("linguafoundry.test")

    logger.debug("service is ready")

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload["level"] == "DEBUG"
    assert payload["logger"] == "linguafoundry.test"
    assert payload["message"] == "service is ready"
    assert "timestamp" in payload
