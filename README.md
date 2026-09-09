# Taelek BLE for Home Assistant

A Home Assistant custom integration for Taelek `ecoControl` Bluetooth thermostats and compatible OEM devices.

Passive advertisement monitoring is always used for live control temperature, mode, relay state, errors, and signal strength. An **opt-in read-only connected poll every 10 minutes** can additionally retrieve the separate sensor temperatures, setpoint, versions, counters, and seven-day heating history. It never pairs or writes.

## Why passive advertisements plus optional polling?

Taelek advertisements already contain useful live telemetry, so those values never require a connection. Separate sensors and lifetime/history counters are only available over GATT. Connected polling is therefore disabled by default and, when enabled under the integration's **Configure** dialog, makes one short read-only connection every 10 minutes and immediately disconnects.

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

### Optional connected-poll sensors

Enable **Settings → Devices & services → Taelek BLE → Configure → Connected polling** to retrieve these every 10 minutes:

- Desired temperature/setpoint
- Separate air, floor, and external temperatures
- Relative humidity, sensor error, operation mode, and device state
- Hardware, software, and bootloader versions; connected device type; melting condition
- Relay cycle count, operating time, and total heating time
- Heating minutes for each of the last six days and today
- Last successful connected poll

Each poll reads only `productInfo`, `productStateA`, `productCountersA`, and `productCounterB`, then disconnects. No pairing or GATT writes are performed.

## Observed advertisement format

After the standard Bluetooth AD wrapper and Taelek company ID are removed, the 18-byte payload is:

- Bytes `0..1`: signed 16-bit little-endian active/control temperature, `0.1 °C`
- Byte `2`: relay bit, state code, and error code
- Byte `3`: product/type discriminator
- Bytes `4..7`: unsigned 32-bit little-endian serial number
- Bytes `8..17`: configured name, UTF-8 and space padded

Observed example:

```text
15 ff 8a 04 d1 00 40 22 89 0b 6b 0e 42 6f 74 69 61 20 20 20 20 20
```

This decodes as `20.9 °C`, Program Eco, heating off, no error, serial `241896329`, and configured name `Botia`.

The format was recovered from ecoControl Android 3.0.5 and cross-checked against ecoControl 3.0.11 on a real thermostat. In Botia's `Floor` mode, the advertised value matched the app's floor temperature (`20.7 °C`) while the air sensor read `26.2 °C`; this indicates that the packet carries the selected control temperature rather than always carrying air temperature. Unknown state codes remain visible as raw diagnostics rather than being guessed.

## Requirements and limitations

- Home Assistant Bluetooth must receive the advertisement and provide a connectable route, either locally or through an ESPHome Bluetooth proxy.
- Connected polling is off by default. The official app must not hold the thermostat's single BLE connection.
- Some thermostats may suspend or alter heating output during a BLE connection. Polls are deliberately brief, but verify behavior on your hardware before leaving the option enabled.
- The advertisement contains one selected control temperature. Separate air, floor, and external readings, setpoints, versions, counters, and daily history are added only after the first successful connected poll.
- Devices do not become available until their first valid advertisement is received after setup.
- Advertisement cadence is controlled by the thermostat.

## Privacy and safety

- No cloud service or internet connection is used.
- Connected polling is explicit opt-in and remains read-only.
- No pairing or GATT writes occur.
- Every connected poll disconnects in a `finally` cleanup path, including read errors and timeouts.
- Neighboring devices are not added unless explicitly selected; ignored discoveries are handled by Home Assistant.

## Development

```bash
uv run --with homeassistant --with aiohasupervisor --with serialx --with bluetooth-adapters --with aiousbwatcher --with pyserial --with pytest python -m pytest
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
```

## License

MIT
