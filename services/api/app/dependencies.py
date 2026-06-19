"""Dependency providers for future domain integration."""

from collections.abc import Mapping


def get_domain_context() -> Mapping[str, str]:
    """Provide a stable hook for routes that will call domain services."""

    return {"status": "not_configured"}
