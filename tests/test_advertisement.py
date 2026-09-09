"""Tests for Taelek manufacturer advertisement decoding."""

from custom_components.taelek_ble.advertisement import (
    COMPANY_ID,
    TaelekAdvertisement,
    parse_manufacturer_data,
)

SAMPLE = bytes.fromhex("d1004022890b6b0e426f7469612020202020")


def test_decode_known_botia_packet() -> None:
    """Decode the observed Botia advertisement."""
    result = parse_manufacturer_data(SAMPLE, rssi=-88)

    assert result == TaelekAdvertisement(
        temperature=20.9,
        state_code=4,
        eco=True,
        comfort=False,
        automatic_program=True,
        boost=False,
        error_code=0,
        heating=False,
        product_type=0x22,
        serial=241896329,
        configured_name="Botia",
        rssi=-88,
    )


def test_decode_heating_comfort_packet() -> None:
    """Decode relay, comfort, and error flags independently."""
    payload = bytearray(SAMPLE)
    payload[0:2] = (-55).to_bytes(2, "little", signed=True)
    payload[2] = 0x80 | 0x10 | 0x08

    result = parse_manufacturer_data(bytes(payload), rssi=-42)

    assert result is not None
    assert result.temperature == -5.5
    assert result.heating is True
    assert result.state_code == 1
    assert result.comfort is True
    assert result.eco is False
    assert result.automatic_program is False
    assert result.error_code == 2


def test_decode_boost_packet() -> None:
    """All-zero state bits represent Boost in ecoControl."""
    payload = bytearray(SAMPLE)
    payload[2] = 0

    result = parse_manufacturer_data(bytes(payload), rssi=None)

    assert result is not None
    assert result.boost is True
    assert result.state_code == 0


def test_reject_short_and_invalid_name_packets() -> None:
    """Reject unrelated or malformed company payloads."""
    assert parse_manufacturer_data(b"\x00" * 17, rssi=-10) is None

    payload = bytearray(SAMPLE)
    payload[8:18] = b"\xff" * 10
    assert parse_manufacturer_data(bytes(payload), rssi=-10) is None


def test_company_id() -> None:
    """Use Taelek's assigned Bluetooth company identifier."""
    assert COMPANY_ID == 0x048A
