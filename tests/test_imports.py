"""Smoke-test every Home Assistant platform module."""


def test_import_all_integration_modules() -> None:
    """Import all modules against the installed Home Assistant API."""
    from custom_components.taelek_ble import (
        binary_sensor,  # noqa: F401, PLC0415
        button,  # noqa: F401, PLC0415
        config_flow,  # noqa: F401, PLC0415
        entity,  # noqa: F401, PLC0415
        sensor,  # noqa: F401, PLC0415
    )
