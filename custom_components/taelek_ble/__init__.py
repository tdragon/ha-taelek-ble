"""The Taelek BLE integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

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
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .advertisement import COMPANY_ID, TaelekAdvertisement, parse_manufacturer_data
from .const import CONF_SERIAL, DOMAIN

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TaelekData:
    """Latest passive data for one thermostat."""

    advertisement: TaelekAdvertisement
    address: str
    last_seen: datetime


class TaelekCoordinator(DataUpdateCoordinator[TaelekData]):
    """Publish advertisements for one configured Taelek serial number."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, serial: int) -> None:
        """Initialize the advertisement coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{serial}",
            always_update=True,
        )
        self.serial = serial

    @callback
    def async_process(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Decode and publish a matching passive advertisement."""
        payload = service_info.manufacturer_data.get(COMPANY_ID)
        if payload is None:
            return
        decoded = parse_manufacturer_data(payload, rssi=service_info.rssi)
        if decoded is None or decoded.serial != self.serial:
            return
        self.async_set_updated_data(
            TaelekData(
                advertisement=decoded,
                address=service_info.address,
                last_seen=datetime.now(UTC),
            )
        )


type TaelekConfigEntry = ConfigEntry[TaelekCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TaelekConfigEntry) -> bool:
    """Set up a Taelek BLE thermostat without connecting to it."""
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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TaelekConfigEntry) -> bool:
    """Unload a Taelek BLE config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
