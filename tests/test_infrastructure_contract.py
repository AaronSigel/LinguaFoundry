import shlex
import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_service_images_install_package_at_build_time_only() -> None:
    api_dockerfile = (REPOSITORY_ROOT / "services/api/Dockerfile").read_text()
    bot_dockerfile = (REPOSITORY_ROOT / "services/bot/Dockerfile").read_text()

    for dockerfile in (api_dockerfile, bot_dockerfile):
        cmd_section = dockerfile.split("CMD ", maxsplit=1)[1]
        assert "python -m pip install --no-cache-dir ." in dockerfile
        assert "pip install -e" not in cmd_section
        assert "\nUSER app\n" in dockerfile


def test_compose_wires_healthchecks_and_bot_readiness_environment() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text()

    assert "urlopen('http://localhost:8000/health', timeout=5).read()" in compose
    assert "condition: service_healthy" in compose
    assert "API_READY_TIMEOUT_SECONDS: ${API_READY_TIMEOUT_SECONDS:-60}" in compose
    assert "API_READY_INTERVAL_SECONDS: ${API_READY_INTERVAL_SECONDS:-2}" in compose


def test_api_settings_are_imported_from_single_module() -> None:
    api_config_path = REPOSITORY_ROOT / "services/api/app/config.py"
    legacy_config_path = REPOSITORY_ROOT / "services/api/app/core/config.py"

    assert api_config_path.exists()
    assert not legacy_config_path.exists()
    assert (
        "from services.api.app.config import get_settings"
        in (REPOSITORY_ROOT / "services/api/app/db/database.py").read_text()
    )
    assert (
        "from services.api.app.config import get_settings"
        in (REPOSITORY_ROOT / "services/api/alembic/env.py").read_text()
    )


def test_ci_markdown_formatting_ignores_tool_cache_readmes(tmp_path: Path) -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text()
    find_start = workflow.index("find . -path ./.git -prune -o \\")
    find_end = workflow.index("| xargs -0 mdformat --check", find_start)
    find_command = workflow[find_start:find_end].replace("\\\n", " ").strip()

    markdown_paths = [
        "README.md",
        "docs/development.md",
        ".pytest_cache/README.md",
        ".ruff_cache/README.md",
        ".github/ISSUE_TEMPLATE/feature.md",
    ]

    for relative_path in markdown_paths:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Test\n")

    result = subprocess.run(
        shlex.split(find_command),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    discovered_paths = set(result.stdout.decode().split("\0"))
    discovered_paths.discard("")

    assert discovered_paths == {"./README.md", "./docs/development.md"}
