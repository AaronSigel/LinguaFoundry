from __future__ import annotations

import asyncio
import tomllib
from pathlib import Path

from services.api.app import lang_packs

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_pyproject_installs_language_pack_cli_entrypoint() -> None:
    pyproject = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["scripts"]["linguafoundry-lang-packs"] == (
        "services.api.app.lang_packs:main"
    )


def test_language_pack_cli_check_validates_without_import(monkeypatch, capsys) -> None:
    async def fail_import(paths: object) -> lang_packs.ImportStats:
        raise AssertionError(f"--check should not import packs: {paths}")

    monkeypatch.setattr(lang_packs, "import_language_pack_files", fail_import)

    exit_code = asyncio.run(
        lang_packs._main_async(["--check", "packages/lang-packs/examples"])
    )

    assert exit_code == 0
    assert capsys.readouterr().out == "Validated 2 language pack file(s).\n"


def test_docker_compose_api_seed_command_is_configurable() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text()

    assert "SEED_LANG_PACKS: ${SEED_LANG_PACKS:-true}" in compose
    assert (
        "SEED_LANG_PACK_PATHS: ${SEED_LANG_PACK_PATHS:-packages/lang-packs/examples}"
        in compose
    )
    assert (
        'if [ \\"$${SEED_LANG_PACKS}\\" = \\"true\\" ]; then '
        "linguafoundry-lang-packs $${SEED_LANG_PACK_PATHS}; fi"
    ) in compose
