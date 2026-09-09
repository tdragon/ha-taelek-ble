"""Config flow for passive Taelek BLE thermostats."""

from __future__ import annotations

from typing import Any, override

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .advertisement import COMPANY_ID, TaelekAdvertisement, parse_manufacturer_data
from .const import (
    CONF_CONFIGURED_NAME,
    CONF_INITIAL_ADDRESS,
    CONF_SERIAL,
    DOMAIN,
)


class TaelekConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle discovery and selection of Taelek BLE devices."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._decoded: TaelekAdvertisement | None = None
        self._discovered_devices: dict[
            str, tuple[BluetoothServiceInfoBleak, TaelekAdvertisement]
        ] = {}

    @staticmethod
    def _decode(
        discovery_info: BluetoothServiceInfoBleak,
    ) -> TaelekAdvertisement | None:
        payload = discovery_info.manufacturer_data.get(COMPANY_ID)
        if payload is None:
            return None
        return parse_manufacturer_data(payload, rssi=discovery_info.rssi)

    @staticmethod
    def _unique_id(decoded: TaelekAdvertisement) -> str:
        return str(decoded.serial)

    @staticmethod
    def _title(decoded: TaelekAdvertisement) -> str:
        return decoded.configured_name or f"Taelek {decoded.serial}"

    @override
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a matching Bluetooth discovery."""
        decoded = self._decode(discovery_info)
        if decoded is None:
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(self._unique_id(decoded))
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self._decoded = decoded
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered thermostat; HA also provides its Ignore action."""
        assert self._discovery_info is not None
        assert self._decoded is not None
        title = self._title(self._decoded)
        placeholders = {
            "name": title,
            "serial": str(self._decoded.serial),
            "address": self._discovery_info.address,
        }
        self.context["title_placeholders"] = placeholders

        if user_input is not None:
            return self.async_create_entry(
                title=title,
                data=self._entry_data(self._discovery_info, self._decoded),
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm", description_placeholders=placeholders
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """List all currently visible, compatible, unconfigured devices."""
        if user_input is not None:
            unique_id = user_input[CONF_SERIAL]
            discovery_info, decoded = self._discovered_devices[unique_id]
            await self.async_set_unique_id(unique_id, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._title(decoded),
                data=self._entry_data(discovery_info, decoded),
            )

        current_ids = self._async_current_ids(include_ignore=False)
        for discovery_info in async_discovered_service_info(self.hass, False):
            decoded = self._decode(discovery_info)
            if decoded is None:
                continue
            unique_id = self._unique_id(decoded)
            if unique_id in current_ids:
                continue
            self._discovered_devices[unique_id] = (discovery_info, decoded)

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        choices = {
            unique_id: (
                f"{decoded.configured_name} — {decoded.serial} — "
                f"{discovery_info.address} ({decoded.rssi} dBm)"
            )
            for unique_id, (discovery_info, decoded) in self._discovered_devices.items()
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_SERIAL): vol.In(choices)}),
        )

    @staticmethod
    def _entry_data(
        discovery_info: BluetoothServiceInfoBleak,
        decoded: TaelekAdvertisement,
    ) -> dict[str, Any]:
        """Build config-entry data from a passive advertisement."""
        return {
            CONF_SERIAL: decoded.serial,
            CONF_CONFIGURED_NAME: decoded.configured_name,
            CONF_INITIAL_ADDRESS: discovery_info.address,
        }
