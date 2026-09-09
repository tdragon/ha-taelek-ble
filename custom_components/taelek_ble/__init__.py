"""The Taelek BLE integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.match import (
    MANUFACTURER_ID,
    BluetoothCallbackMatcher,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .advertisement import COMPANY_ID, TaelekAdvertisement, parse_manufacturer_data
from .const import (
    CONF_ACTIVE_POLLING,
    CONF_INITIAL_ADDRESS,
    CONF_SERIAL,
    DOMAIN,
    POLL_INTERVAL,
    POLL_RETRY_DELAYS,
)
from .gatt import TaelekGattData, async_poll_gatt

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
]
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TaelekData:
    """Latest passive and optional connected data for one thermostat."""

    address: str
    advertisement: TaelekAdvertisement | None = None
    last_seen: datetime | None = None
    gatt: TaelekGattData | None = None
    last_poll_attempt: datetime | None = None
    last_polled: datetime | None = None
    poll_error: str | None = None


class TaelekCoordinator(DataUpdateCoordinator[TaelekData]):
    """Publish advertisements and optionally poll connected GATT data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, serial: int) -> None:
        """Initialize the coordinator."""
        self.serial = serial
        self.active_polling = bool(entry.options.get(CONF_ACTIVE_POLLING, False))
        self._force_query_requested = False
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{serial}",
            always_update=True,
            # A dedicated interval callback schedules connected polling. Passive
            # advertisement updates must never influence that clock.
            update_interval=None,
        )
        self.data = TaelekData(address=str(entry.data[CONF_INITIAL_ADDRESS]))

    @callback
    def async_process(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Decode and publish a matching passive advertisement."""
        payload = service_info.manufacturer_data.get(COMPANY_ID)
        if payload is None:
            return
        decoded = parse_manufacturer_data(payload, rssi=service_info.rssi)
        if decoded is None or decoded.serial != self.serial:
            return
        # Do not use async_set_updated_data here: it resets the coordinator's
        # refresh timer. Since this device advertises frequently, doing so would
        # postpone the periodic GATT poll indefinitely.
        self.data = replace(
            self.data,
            advertisement=decoded,
            address=service_info.address,
            last_seen=datetime.now(UTC),
        )
        self.async_update_listeners()

    async def async_force_query(self) -> None:
        """Make one immediate read-only query regardless of the periodic option."""
        self._force_query_requested = True
        try:
            await self.async_refresh()
        finally:
            self._force_query_requested = False

    async def _async_update_data(self) -> TaelekData:
        """Make one short read-only connection when polling is requested."""
        if not self.active_polling and not self._force_query_requested:
            return self.data

        address = self.data.address
        attempts = len(POLL_RETRY_DELAYS) + 1
        error = ""
        attempted_at = datetime.now(UTC)

        for attempt in range(attempts):
            attempted_at = datetime.now(UTC)
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, address, connectable=True
            )
            if ble_device is None:
                error = f"No connectable Bluetooth route for {address}"
            else:
                try:
                    gatt_data = await async_poll_gatt(
                        ble_device,
                        self.data.advertisement.configured_name
                        if self.data.advertisement
                        else self.config_entry.title,
                    )
                except Exception as err:  # BLE and read failures are transient
                    error = f"{type(err).__name__}: {err}"
                else:
                    return replace(
                        self.data,
                        gatt=gatt_data,
                        last_poll_attempt=attempted_at,
                        last_polled=datetime.now(UTC),
                        poll_error=None,
                    )

            if attempt < len(POLL_RETRY_DELAYS):
                delay = POLL_RETRY_DELAYS[attempt]
                _LOGGER.debug(
                    "GATT poll attempt %s/%s failed for %s: %s; retrying in %ss",
                    attempt + 1,
                    attempts,
                    self.serial,
                    error,
                    delay,
                )
                await asyncio.sleep(delay)

        _LOGGER.warning(
            "GATT poll failed after %s attempts for %s: %s",
            attempts,
            self.serial,
            error,
        )
        return replace(self.data, last_poll_attempt=attempted_at, poll_error=error)


type TaelekConfigEntry = ConfigEntry[TaelekCoordinator]


async def _async_reload_entry(hass: HomeAssistant, entry: TaelekConfigEntry) -> None:
    """Reload after the active-polling option changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: TaelekConfigEntry) -> bool:
    """Set up a Taelek BLE thermostat."""
    coordinator = TaelekCoordinator(hass, entry, int(entry.data[CONF_SERIAL]))
    entry.runtime_data = coordinator

    @callback
    def _async_advertisement(
        service_info: BluetoothServiceInfoBleak, _change: BluetoothChange
    ) -> None:
        coordinator.async_process(service_info)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_advertisement,
            BluetoothCallbackMatcher({MANUFACTURER_ID: COMPANY_ID}),
            BluetoothScanningMode.PASSIVE,
        )
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if coordinator.active_polling:

        async def _async_periodic_poll(_now: datetime) -> None:
            """Request one connected poll without resetting this interval."""
            await coordinator.async_request_refresh()

        entry.async_on_unload(
            async_track_time_interval(
                hass,
                _async_periodic_poll,
                timedelta(seconds=POLL_INTERVAL),
            )
        )
        entry.async_create_background_task(
            hass,
            coordinator.async_refresh(),
            name=f"{DOMAIN}_{coordinator.serial}_initial_poll",
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TaelekConfigEntry) -> bool:
    """Unload a Taelek BLE config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
