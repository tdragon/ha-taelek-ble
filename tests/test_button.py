"""Tests for the manual read-only GATT query button."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.taelek_ble import TaelekCoordinator
from custom_components.taelek_ble.button import TaelekForceQueryButton


def test_force_query_coordinator_bypasses_periodic_option() -> None:
    """The forced path marks the next refresh as an explicit query."""
    coordinator = object.__new__(TaelekCoordinator)
    coordinator._force_query_requested = False

    async def assert_forced() -> None:
        assert coordinator._force_query_requested is True

    coordinator.async_refresh = AsyncMock(side_effect=assert_forced)

    asyncio.run(coordinator.async_force_query())

    coordinator.async_refresh.assert_awaited_once_with()
    assert coordinator._force_query_requested is False


def test_force_query_button_requests_an_immediate_poll() -> None:
    """Pressing the button must invoke the coordinator's forced query path."""
    force_query = AsyncMock()
    entity = object.__new__(TaelekForceQueryButton)
    entity.coordinator = SimpleNamespace(async_force_query=force_query)

    asyncio.run(entity.async_press())

    force_query.assert_awaited_once_with()
