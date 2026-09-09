"""Tests for stable decoded mode names."""

from custom_components.taelek_ble.advertisement import parse_manufacturer_data

BASE = bytes.fromhex("d1000022890b6b0e426f7469612020202020")


def _mode(state_code: int) -> str:
    payload = bytearray(BASE)
    payload[2] = state_code << 4
    decoded = parse_manufacturer_data(bytes(payload), rssi=None)
    assert decoded is not None
    return decoded.mode


def test_modes() -> None:
    """Map all currently understood ecoControl list-screen states."""
    assert _mode(0) == "boost"
    assert _mode(1) == "comfort"
    assert _mode(2) == "eco"
    assert _mode(3) == "automatic_comfort"
    assert _mode(4) == "automatic_eco"
    assert _mode(5) == "unknown"
    assert _mode(6) == "eco_state_6"
    assert _mode(7) == "unknown"
