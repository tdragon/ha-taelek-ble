# Taelek BLE for Home Assistant

A read-only Home Assistant custom integration for Taelek `ecoControl` Bluetooth thermostats and compatible OEM devices.

It listens to manufacturer advertisements through Home Assistant Bluetooth—including ESPHome Bluetooth proxies—and **never connects, pairs, writes, or changes thermostat settings**.

## Why passive advertisements?

Taelek advertisements already contain useful live telemetry. Some thermostats also appear to allow only one BLE central or may change behavior while the official app maintains a connection. This integration therefore uses advertisement data only.

## Installation with HACS

1. Open HACS → **Integrations**.
2. Open the menu → **Custom repositories**.
3. Add `https://github.com/tdragon/ha-taelek-ble` with category **Integration**.
4. Find **Taelek BLE**, download it, and restart Home Assistant.
5. Open **Settings → Devices & services → Add integration → Taelek BLE**.

After HACS knows the repository, this shortcut opens it:

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tdragon&repository=ha-taelek-ble&category=integration)

## Device discovery and neighbors

The integration recognizes Bluetooth company ID `0x048A` (Taelek Oy) and validates the payload before offering a device.

- Home Assistant creates a standard discovery card for each compatible device, where you can **Add** or **Ignore** it.
- Starting **Add integration → Taelek BLE** manually lists all currently visible compatible, unconfigured devices with configured name, serial number, address, and RSSI.
- The embedded serial number is used as the stable identity, rather than the Bluetooth address.
- Ignoring a neighbor's discovery card does not prevent you from adding it later through the manual list.

The configured thermostat name embedded in the advertisement—such as `Botia`—is used as the Home Assistant device name and is also exposed as a diagnostic sensor.

## Entities

### Sensors

- Temperature
- Mode: Boost, Comfort, Eco, Program comfort, or Program eco
- Configured name
- Raw state code
- Error code
- Bluetooth signal strength
- Last seen

### Binary sensors

- Heating/output relay
- Eco
- Comfort
- Automatic program
- Boost
- Error

## Observed advertisement format

After the standard Bluetooth AD wrapper and Taelek company ID are removed, the 18-byte payload is:

- Bytes `0..1`: signed 16-bit little-endian temperature, `0.1 °C`
- Byte `2`: relay bit, state code, and error code
- Byte `3`: product/type discriminator
- Bytes `4..7`: unsigned 32-bit little-endian serial number
- Bytes `8..17`: configured name, UTF-8 and space padded

Observed example:

```text
15 ff 8a 04 d1 00 40 22 89 0b 6b 0e 42 6f 74 69 61 20 20 20 20 20
```

This decodes as `20.9 °C`, Program Eco, heating off, no error, serial `241896329`, and configured name `Botia`.

The format was recovered from ecoControl Android 3.0.5 and validated against an observed thermostat advertisement. Unknown state codes remain visible as raw diagnostics rather than being guessed.

## Requirements and limitations

- Home Assistant Bluetooth must receive the advertisement, either locally or through an ESPHome Bluetooth proxy.
- No historical values, setpoint, floor temperature, or cumulative counters are present in this advertisement; those require a GATT connection and are intentionally not accessed.
- Devices do not become available until their first valid advertisement is received after setup.
- Advertisement cadence is controlled by the thermostat.

## Privacy and safety

- No cloud service or internet connection is used.
- No BLE connection is opened.
- No pairing or GATT reads/writes occur.
- Neighboring devices are not added unless explicitly selected; ignored discoveries are handled by Home Assistant.

## Development

```bash
uv run --with homeassistant --with bluetooth-adapters --with aiousbwatcher --with pyserial --with pytest python -m pytest
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
```

## License

MIT
