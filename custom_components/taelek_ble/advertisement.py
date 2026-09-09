"""Decode passive Taelek ecoControl BLE advertisements."""

from __future__ import annotations

from dataclasses import dataclass

COMPANY_ID = 0x048A
PAYLOAD_LENGTH = 18


@dataclass(frozen=True, slots=True)
class TaelekAdvertisement:
    """Decoded Taelek manufacturer advertisement."""

    temperature: float | None
    state_code: int
    eco: bool
    comfort: bool
    automatic_program: bool
    boost: bool
    error_code: int
    heating: bool
    product_type: int
    serial: int
    configured_name: str
    rssi: int | None

    @property
    def mode(self) -> str:
        """Return a stable human-readable mode key."""
        if self.boost:
            return "boost"
        if self.state_code == 1:
            return "comfort"
        if self.state_code == 2:
            return "eco"
        if self.state_code == 3:
            return "automatic_comfort"
        if self.state_code == 4:
            return "automatic_eco"
        if self.state_code == 6:
            return "eco_state_6"
        return "unknown"


def parse_manufacturer_data(
    payload: bytes, *, rssi: int | None
) -> TaelekAdvertisement | None:
    """Decode a Taelek company payload, returning None when malformed."""
    if len(payload) < PAYLOAD_LENGTH:
        return None

    try:
        configured_name = payload[8:18].decode("utf-8").strip(" \x00")
    except UnicodeDecodeError:
        return None
    if not configured_name:
        return None

    temperature_raw_unsigned = int.from_bytes(payload[0:2], "little")
    temperature = (
        None
        if temperature_raw_unsigned == 0xFFFF
        else int.from_bytes(payload[0:2], "little", signed=True) / 10
    )
    status = payload[2]
    state_code = (status & 0x70) >> 4

    return TaelekAdvertisement(
        temperature=temperature,
        state_code=state_code,
        eco=state_code in (2, 4, 6),
        comfort=state_code in (1, 3),
        automatic_program=state_code in (3, 4),
        boost=(status & 0x70) == 0,
        error_code=(status & 0x0C) >> 2,
        heating=bool(status & 0x80),
        product_type=payload[3],
        serial=int.from_bytes(payload[4:8], "little"),
        configured_name=configured_name,
        rssi=rssi,
    )
