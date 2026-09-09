"""Read-only Taelek ecoControl GATT protocol support."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

SERVICE_UUID = "2be32db1-5f6b-4cbd-8803-38d6dfb16490"
PRODUCT_INFO_UUID = "2be32db1-5f6b-4cbd-8813-8d6dfb164900"
PRODUCT_STATE_UUID = "2be32db1-5f6b-4cbd-8843-8d6dfb164900"
TOTAL_COUNTERS_UUID = "2be32db1-5f6b-4cbd-8863-8d6dfb164900"
DAILY_HEATING_UUID = "2be32db1-5f6b-4cbd-8873-8d6dfb164900"


class GattPayloadError(ValueError):
    """Raised when a GATT characteristic has an invalid payload."""


@dataclass(frozen=True, slots=True)
class ProductInfo:
    """Static product information returned by the thermostat."""

    product_number: str
    last_melting_reason: int
    hardware_version: str
    software_version: int
    bootloader_version: int
    device_type: int


@dataclass(frozen=True, slots=True)
class ProductState:
    """Current connected-state telemetry."""

    humidity: int
    sensor_error: int
    operation_mode: int
    device_state: int
    setpoint: float
    air_temperature: float
    floor_temperature: float
    external_temperature: float

    @property
    def device_state_name(self) -> str:
        """Translate known valve/output state values without guessing unknowns."""
        return {
            0: "temperature_balanced",
            1: "heating",
            2: "cooling",
        }.get(self.device_state, "unknown")


@dataclass(frozen=True, slots=True)
class TotalCounters:
    """Lifetime thermostat counters."""

    relay_cycle_count: int
    operating_time_hours: int
    heating_time_hours: float


@dataclass(frozen=True, slots=True)
class DailyHeating:
    """Heating minutes from six days ago through today."""

    minutes: tuple[int, int, int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class TaelekGattData:
    """Complete result of one short, read-only polling connection."""

    product_info: ProductInfo
    state: ProductState
    counters: TotalCounters
    daily_heating: DailyHeating


def _require_length(payload: bytes, expected: int, characteristic: str) -> None:
    if len(payload) < expected:
        raise GattPayloadError(
            f"{characteristic} payload is {len(payload)} bytes; "
            f"expected at least {expected}"
        )


def _text(payload: bytes) -> str:
    return payload.decode("utf-8", errors="replace").strip(" \x00")


def parse_product_info(payload: bytes) -> ProductInfo:
    """Decode the 17-byte productInfo characteristic."""
    _require_length(payload, 17, "productInfo")
    return ProductInfo(
        product_number=_text(payload[0:9]),
        last_melting_reason=payload[9],
        hardware_version=_text(payload[10:14]),
        software_version=payload[14],
        bootloader_version=payload[15],
        device_type=payload[16],
    )


def _temperature(payload: bytes, offset: int) -> float:
    return int.from_bytes(payload[offset : offset + 2], "little", signed=True) / 10


def parse_product_state(payload: bytes) -> ProductState:
    """Decode the 12-byte productStateA characteristic."""
    _require_length(payload, 12, "productStateA")
    return ProductState(
        humidity=payload[0],
        sensor_error=payload[1],
        operation_mode=payload[2],
        device_state=payload[3],
        setpoint=_temperature(payload, 4),
        air_temperature=_temperature(payload, 6),
        floor_temperature=_temperature(payload, 8),
        external_temperature=_temperature(payload, 10),
    )


def parse_total_counters(payload: bytes) -> TotalCounters:
    """Decode the 12-byte productCountersA characteristic."""
    _require_length(payload, 12, "productCountersA")
    return TotalCounters(
        relay_cycle_count=int.from_bytes(payload[0:4], "little"),
        operating_time_hours=int.from_bytes(payload[4:8], "little"),
        heating_time_hours=int.from_bytes(payload[8:12], "little") * 0.01,
    )


def parse_daily_heating(payload: bytes) -> DailyHeating:
    """Decode seven uint16 heating-minute values, oldest through today."""
    _require_length(payload, 14, "productCounterB")
    values = tuple(
        int.from_bytes(payload[offset : offset + 2], "little")
        for offset in range(0, 14, 2)
    )
    return DailyHeating(minutes=values)  # type: ignore[arg-type]


async def async_poll_gatt(ble_device: Any, name: str) -> TaelekGattData:
    """Connect, perform only four reads, and always disconnect promptly."""
    # Imports stay local so the payload decoder remains independently testable.
    from bleak import BleakClient  # noqa: PLC0415
    from bleak_retry_connector import establish_connection  # noqa: PLC0415

    client = await establish_connection(
        BleakClient,
        ble_device,
        name,
        # The coordinator owns bounded retries so every attempt gets a fresh
        # Home Assistant Bluetooth route and also covers transient read errors.
        max_attempts=1,
        use_services_cache=True,
        pair=False,
    )
    try:
        async with asyncio.timeout(20):
            product_info = bytes(await client.read_gatt_char(PRODUCT_INFO_UUID))
            product_state = bytes(await client.read_gatt_char(PRODUCT_STATE_UUID))
            total_counters = bytes(await client.read_gatt_char(TOTAL_COUNTERS_UUID))
            daily_heating = bytes(await client.read_gatt_char(DAILY_HEATING_UUID))
    finally:
        await client.disconnect()

    return TaelekGattData(
        product_info=parse_product_info(product_info),
        state=parse_product_state(product_state),
        counters=parse_total_counters(total_counters),
        daily_heating=parse_daily_heating(daily_heating),
    )
