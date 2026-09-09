"""Tests for read-only Taelek GATT payload decoding."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from custom_components.taelek_ble.const import POLL_INTERVAL
from custom_components.taelek_ble.gatt import (
    GattPayloadError,
    async_poll_gatt,
    parse_daily_heating,
    parse_product_info,
    parse_product_state,
    parse_total_counters,
)


def test_parse_product_info() -> None:
    payload = b"241896329" + bytes([0]) + b"1.6S" + bytes([54, 14, 10])

    info = parse_product_info(payload)

    assert info.product_number == "241896329"
    assert info.last_melting_reason == 0
    assert info.hardware_version == "1.6S"
    assert info.software_version == 54
    assert info.bootloader_version == 14
    assert info.device_type == 10


def test_parse_product_state() -> None:
    payload = bytes([0, 0, 1, 0])
    payload += (210).to_bytes(2, "little", signed=True)
    payload += (262).to_bytes(2, "little", signed=True)
    payload += (207).to_bytes(2, "little", signed=True)
    payload += (0).to_bytes(2, "little", signed=True)

    state = parse_product_state(payload)

    assert state.humidity == 0
    assert state.sensor_error == 0
    assert state.operation_mode == 1
    assert state.device_state == 0
    assert state.device_state_name == "temperature_balanced"
    assert state.setpoint == 21.0
    assert state.air_temperature == 26.2
    assert state.floor_temperature == 20.7
    assert state.external_temperature == 0.0


def test_parse_total_counters() -> None:
    payload = (123).to_bytes(4, "little")
    payload += (4567).to_bytes(4, "little")
    payload += (8912).to_bytes(4, "little")

    counters = parse_total_counters(payload)

    assert counters.relay_cycle_count == 123
    assert counters.operating_time_hours == 4567
    assert counters.heating_time_hours == 89.12


def test_parse_daily_heating_oldest_to_today() -> None:
    payload = b"".join(value.to_bytes(2, "little") for value in range(7))

    history = parse_daily_heating(payload)

    assert history.minutes == (0, 1, 2, 3, 4, 5, 6)


@pytest.mark.parametrize(
    ("parser", "payload"),
    [
        (parse_product_info, bytes(16)),
        (parse_product_state, bytes(11)),
        (parse_total_counters, bytes(11)),
        (parse_daily_heating, bytes(13)),
    ],
)
def test_short_payload_is_rejected(parser, payload: bytes) -> None:
    with pytest.raises(GattPayloadError):
        parser(payload)


def test_poll_interval_is_exactly_ten_minutes() -> None:
    assert POLL_INTERVAL == 600


def test_connected_poll_reads_only_known_characteristics_and_disconnects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.taelek_ble import gatt

    product = b"123456789" + b"\x00" + b"1.6S" + bytes([54, 14, 10])
    state = bytes([42, 0, 1, 2]) + b"".join(
        value.to_bytes(2, "little", signed=True) for value in [210, 262, 207, 0]
    )
    counters = b"".join(
        value.to_bytes(4, "little") for value in [10768, 32314, 1_093_610]
    )
    daily = b"".join(value.to_bytes(2, "little") for value in [0, 1, 2, 3, 4, 358, 24])
    payloads = {
        gatt.PRODUCT_INFO_UUID: product,
        gatt.PRODUCT_STATE_UUID: state,
        gatt.TOTAL_COUNTERS_UUID: counters,
        gatt.DAILY_HEATING_UUID: daily,
    }

    client = AsyncMock()
    client.read_gatt_char.side_effect = lambda uuid: payloads[uuid]
    establish = AsyncMock(return_value=client)
    monkeypatch.setattr("bleak_retry_connector.establish_connection", establish)

    result = asyncio.run(async_poll_gatt(object(), "Botia"))

    assert result.state.floor_temperature == 20.7
    assert result.counters.heating_time_hours == 10936.1
    assert result.daily_heating.minutes[-2:] == (358, 24)
    assert [call.args[0] for call in client.read_gatt_char.await_args_list] == list(
        payloads
    )
    client.disconnect.assert_awaited_once()
    assert establish.await_args.kwargs["pair"] is False


def test_connected_poll_disconnects_when_a_read_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = AsyncMock()
    client.read_gatt_char.side_effect = RuntimeError("read failed")
    establish = AsyncMock(return_value=client)
    monkeypatch.setattr("bleak_retry_connector.establish_connection", establish)

    with pytest.raises(RuntimeError, match="read failed"):
        asyncio.run(async_poll_gatt(object(), "Botia"))

    client.disconnect.assert_awaited_once()
