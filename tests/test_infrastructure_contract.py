import shlex
import subprocess
from configparser import ConfigParser
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCE_ROOTS = ("services", "packages", "tests")


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
    legacy_core_path = REPOSITORY_ROOT / "services/api/app/core"
    legacy_config_path = REPOSITORY_ROOT / "services/api/app/core/config.py"

    assert api_config_path.exists()
    assert not legacy_core_path.exists()
    assert not legacy_config_path.exists()
    assert (
        "from services.api.app.config import get_settings"
        in (REPOSITORY_ROOT / "services/api/app/db/database.py").read_text()
    )
    assert (
        "from services.api.app.config import get_settings"
        in (REPOSITORY_ROOT / "services/api/alembic/env.py").read_text()
    )


def test_legacy_api_core_package_is_not_referenced() -> None:
    legacy_references = []
    legacy_import = ".".join(("services", "api", "app", "core"))
    legacy_path = "/".join(("services", "api", "app", "core"))

    for source_root in PYTHON_SOURCE_ROOTS:
        for path in (REPOSITORY_ROOT / source_root).rglob("*.py"):
            if path == Path(__file__).resolve():
                continue

            text = path.read_text()
            if legacy_import in text or legacy_path in text:
                legacy_references.append(path.relative_to(REPOSITORY_ROOT).as_posix())

    assert legacy_references == []


def test_pytest_asyncio_fixture_loop_scope_is_explicit() -> None:
    config = ConfigParser()
    config.read(REPOSITORY_ROOT / "pytest.ini")

    assert config.get("pytest", "asyncio_default_fixture_loop_scope") == "function"


def test_api_readme_documents_current_service_modules() -> None:
    api_readme = (REPOSITORY_ROOT / "services/api/README.md").read_text()

    expected_entries = {
        "- `app/db`:": REPOSITORY_ROOT / "services/api/app/db",
        "- `app/lang_packs.py`:": REPOSITORY_ROOT / "services/api/app/lang_packs.py",
        "- `app/logging.py`:": REPOSITORY_ROOT / "services/api/app/logging.py",
    }

    for entry, path in expected_entries.items():
        assert entry in api_readme
        assert path.exists()

    assert "app/dependencies.py" not in api_readme
    assert not (REPOSITORY_ROOT / "services/api/app/dependencies.py").exists()


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
