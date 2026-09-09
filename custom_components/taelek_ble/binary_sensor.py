"""Binary sensor entities for passive Taelek advertisements."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TaelekConfigEntry, TaelekData
from .entity import TaelekEntity


@dataclass(frozen=True, kw_only=True)
class TaelekBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a Taelek binary sensor."""

    value_fn: Callable[[TaelekData], bool]


BINARY_SENSORS: tuple[TaelekBinarySensorEntityDescription, ...] = (
    TaelekBinarySensorEntityDescription(
        key="heating",
        translation_key="heating",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda data: data.advertisement.heating,
    ),
    TaelekBinarySensorEntityDescription(
        key="eco",
        translation_key="eco",
        value_fn=lambda data: data.advertisement.eco,
    ),
    TaelekBinarySensorEntityDescription(
        key="comfort",
        translation_key="comfort",
        value_fn=lambda data: data.advertisement.comfort,
    ),
    TaelekBinarySensorEntityDescription(
        key="automatic_program",
        translation_key="automatic_program",
        value_fn=lambda data: data.advertisement.automatic_program,
    ),
    TaelekBinarySensorEntityDescription(
        key="boost",
        translation_key="boost",
        value_fn=lambda data: data.advertisement.boost,
    ),
    TaelekBinarySensorEntityDescription(
        key="error",
        translation_key="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.advertisement.error_code != 0,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: TaelekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Taelek binary sensors."""
    async_add_entities(
        TaelekBinarySensor(entry.runtime_data, description)
        for description in BINARY_SENSORS
    )


class TaelekBinarySensor(TaelekEntity, BinarySensorEntity):
    """Representation of one decoded boolean advertisement field."""

    entity_description: TaelekBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: Any,
        description: TaelekBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the latest decoded boolean value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
