"""Sensor entities for passive Taelek advertisements."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TaelekConfigEntry, TaelekData
from .entity import TaelekEntity


@dataclass(frozen=True, kw_only=True)
class TaelekSensorEntityDescription(SensorEntityDescription):
    """Describe a Taelek sensor."""

    value_fn: Callable[[TaelekData], Any]


SENSORS: tuple[TaelekSensorEntityDescription, ...] = (
    TaelekSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.advertisement.temperature,
    ),
    TaelekSensorEntityDescription(
        key="mode",
        translation_key="mode",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "boost",
            "comfort",
            "eco",
            "automatic_comfort",
            "automatic_eco",
            "eco_state_6",
            "unknown",
        ],
        value_fn=lambda data: data.advertisement.mode,
    ),
    TaelekSensorEntityDescription(
        key="configured_name",
        translation_key="configured_name",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.advertisement.configured_name,
    ),
    TaelekSensorEntityDescription(
        key="state_code",
        translation_key="state_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.advertisement.state_code,
    ),
    TaelekSensorEntityDescription(
        key="error_code",
        translation_key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.advertisement.error_code,
    ),
    TaelekSensorEntityDescription(
        key="signal_strength",
        translation_key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.advertisement.rssi,
    ),
    TaelekSensorEntityDescription(
        key="last_seen",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_seen,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: TaelekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Taelek sensors."""
    async_add_entities(
        TaelekSensor(entry.runtime_data, description) for description in SENSORS
    )


class TaelekSensor(TaelekEntity, SensorEntity):
    """Representation of one decoded advertisement field."""

    entity_description: TaelekSensorEntityDescription

    def __init__(
        self,
        coordinator: Any,
        description: TaelekSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | str | datetime | None:
        """Return the latest decoded value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
