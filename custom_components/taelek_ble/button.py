"""Manual read-only query button for Taelek BLE."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TaelekCoordinator
from .entity import TaelekEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[TaelekCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the manual query button."""
    async_add_entities([TaelekForceQueryButton(entry.runtime_data)])


class TaelekForceQueryButton(TaelekEntity, ButtonEntity):
    """Trigger one immediate, read-only connected query."""

    _attr_translation_key = "force_query"
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, coordinator: TaelekCoordinator) -> None:
        """Initialize the force-query button."""
        super().__init__(coordinator, "force_query")

    async def async_press(self) -> None:
        """Request one immediate connected query regardless of periodic polling."""
        await self.coordinator.async_force_query()
