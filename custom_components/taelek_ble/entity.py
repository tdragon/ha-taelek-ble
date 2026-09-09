"""Base entity for the Taelek BLE integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TaelekCoordinator
from .const import DOMAIN, MANUFACTURER


class TaelekEntity(CoordinatorEntity[TaelekCoordinator]):
    """Base class for entities updated by passive advertisements."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TaelekCoordinator, key: str) -> None:
        """Initialize a Taelek entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_{key}"

    @property
    def available(self) -> bool:
        """Return true after at least one valid advertisement was received."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.advertisement is not None
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return thermostat device information."""
        data = self.coordinator.data
        if data is None or data.advertisement is None:
            return DeviceInfo(
                identifiers={(DOMAIN, str(self.coordinator.serial))},
                manufacturer=MANUFACTURER,
                name=self.coordinator.config_entry.title,
                serial_number=str(self.coordinator.serial),
            )
        advertisement = data.advertisement
        return DeviceInfo(
            identifiers={(DOMAIN, str(advertisement.serial))},
            manufacturer=MANUFACTURER,
            model=f"ecoControl BLE type 0x{advertisement.product_type:02X}",
            name=advertisement.configured_name,
            serial_number=str(advertisement.serial),
        )
