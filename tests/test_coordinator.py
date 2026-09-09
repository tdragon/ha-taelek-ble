"""Tests for coordinator scheduling and resilient connected polling."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.taelek_ble import TaelekCoordinator, TaelekData
from custom_components.taelek_ble.const import POLL_RETRY_DELAYS


def test_advertisement_does_not_reset_periodic_poll_timer() -> None:
    """Frequent advertisements must not postpone the ten-minute refresh forever."""
    coordinator = object.__new__(TaelekCoordinator)
    coordinator.serial = 241896329
    coordinator.data = TaelekData(address="F3:49:B8:73:D3:C2")
    coordinator.async_set_updated_data = Mock()
    coordinator.async_update_listeners = Mock()
    service_info = SimpleNamespace(
        manufacturer_data={
            0x048A: bytes.fromhex("D4004022890B6B0E426F7469612020202020")
        },
        rssi=-84,
        address="F3:49:B8:73:D3:C2",
    )

    coordinator.async_process(service_info)

    coordinator.async_set_updated_data.assert_not_called()
    coordinator.async_update_listeners.assert_called_once_with()
    assert coordinator.data.last_seen is not None


def test_connected_poll_retries_transient_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A scheduled poll gets three bounded chances before being marked failed."""
    coordinator = object.__new__(TaelekCoordinator)
    coordinator.serial = 241896329
    coordinator.active_polling = True
    coordinator._force_query_requested = False
    coordinator.data = TaelekData(address="F3:49:B8:73:D3:C2")
    coordinator.hass = object()
    coordinator.config_entry = SimpleNamespace(title="Botia")

    ble_device = object()
    lookup = Mock(return_value=ble_device)
    expected = object()
    poll = AsyncMock(side_effect=[RuntimeError("one"), RuntimeError("two"), expected])
    sleep = AsyncMock()
    monkeypatch.setattr(
        "custom_components.taelek_ble.bluetooth.async_ble_device_from_address", lookup
    )
    monkeypatch.setattr("custom_components.taelek_ble.async_poll_gatt", poll)
    monkeypatch.setattr("custom_components.taelek_ble.asyncio.sleep", sleep)

    result = asyncio.run(coordinator._async_update_data())

    assert result.gatt is expected
    assert result.poll_error is None
    assert result.last_polled is not None
    assert poll.await_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == list(POLL_RETRY_DELAYS)
