"""Sensor entities for Taelek advertisements and optional GATT polls."""

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
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TaelekConfigEntry, TaelekData
from .entity import TaelekEntity


@dataclass(frozen=True, kw_only=True)
class TaelekSensorEntityDescription(SensorEntityDescription):
    """Describe a Taelek sensor."""

    value_fn: Callable[[TaelekData], Any]
    requires_gatt: bool = False
    requires_success: bool = True


def _gatt_value(path: str) -> Callable[[TaelekData], Any]:
    """Create a getter for a two-level GATT dataclass path."""
    group, field = path.split(".", 1)

    def _get(data: TaelekData) -> Any:
        if data.gatt is None:
            return None
        return getattr(getattr(data.gatt, group), field)

    return _get


def _daily(index: int) -> Callable[[TaelekData], int | None]:
    def _get(data: TaelekData) -> int | None:
        if data.gatt is None:
            return None
        return data.gatt.daily_heating.minutes[index]

    return _get


SENSORS: tuple[TaelekSensorEntityDescription, ...] = (
    TaelekSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: (
            data.advertisement.temperature if data.advertisement else None
        ),
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
        value_fn=lambda data: data.advertisement.mode if data.advertisement else None,
    ),
    TaelekSensorEntityDescription(
        key="configured_name",
        translation_key="configured_name",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.advertisement.configured_name if data.advertisement else None
        ),
    ),
    TaelekSensorEntityDescription(
        key="state_code",
        translation_key="state_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.advertisement.state_code if data.advertisement else None
        ),
    ),
    TaelekSensorEntityDescription(
        key="error_code",
        translation_key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.advertisement.error_code if data.advertisement else None
        ),
    ),
    TaelekSensorEntityDescription(
        key="signal_strength",
        translation_key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.advertisement.rssi if data.advertisement else None,
    ),
    TaelekSensorEntityDescription(
        key="last_seen",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_seen,
    ),
    TaelekSensorEntityDescription(
        key="setpoint",
        translation_key="setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        requires_gatt=True,
        value_fn=_gatt_value("state.setpoint"),
    ),
    TaelekSensorEntityDescription(
        key="air_temperature",
        translation_key="air_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        requires_gatt=True,
        value_fn=_gatt_value("state.air_temperature"),
    ),
    TaelekSensorEntityDescription(
        key="floor_temperature",
        translation_key="floor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        requires_gatt=True,
        value_fn=_gatt_value("state.floor_temperature"),
    ),
    TaelekSensorEntityDescription(
        key="external_temperature",
        translation_key="external_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        requires_gatt=True,
        value_fn=_gatt_value("state.external_temperature"),
    ),
    TaelekSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        requires_gatt=True,
        value_fn=_gatt_value("state.humidity"),
    ),
    TaelekSensorEntityDescription(
        key="sensor_error",
        translation_key="sensor_error",
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        value_fn=_gatt_value("state.sensor_error"),
    ),
    TaelekSensorEntityDescription(
        key="operation_mode",
        translation_key="operation_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        value_fn=_gatt_value("state.operation_mode"),
    ),
    TaelekSensorEntityDescription(
        key="device_state",
        translation_key="device_state",
        device_class=SensorDeviceClass.ENUM,
        options=["temperature_balanced", "heating", "cooling", "unknown"],
        requires_gatt=True,
        value_fn=_gatt_value("state.device_state_name"),
    ),
    TaelekSensorEntityDescription(
        key="melting_condition",
        translation_key="melting_condition",
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        value_fn=_gatt_value("product_info.last_melting_reason"),
    ),
    TaelekSensorEntityDescription(
        key="hardware_version",
        translation_key="hardware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        value_fn=_gatt_value("product_info.hardware_version"),
    ),
    TaelekSensorEntityDescription(
        key="software_version",
        translation_key="software_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        value_fn=_gatt_value("product_info.software_version"),
    ),
    TaelekSensorEntityDescription(
        key="bootloader_version",
        translation_key="bootloader_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        value_fn=_gatt_value("product_info.bootloader_version"),
    ),
    TaelekSensorEntityDescription(
        key="device_type",
        translation_key="device_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        value_fn=_gatt_value("product_info.device_type"),
    ),
    TaelekSensorEntityDescription(
        key="relay_cycle_count",
        translation_key="relay_cycle_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        requires_gatt=True,
        value_fn=_gatt_value("counters.relay_cycle_count"),
    ),
    TaelekSensorEntityDescription(
        key="operating_time",
        translation_key="operating_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        requires_gatt=True,
        value_fn=_gatt_value("counters.operating_time_hours"),
    ),
    TaelekSensorEntityDescription(
        key="total_heating_time",
        translation_key="total_heating_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        requires_gatt=True,
        value_fn=_gatt_value("counters.heating_time_hours"),
    ),
    *(
        TaelekSensorEntityDescription(
            key=f"heating_minutes_day_{index}",
            translation_key=f"heating_minutes_day_{index}",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.MINUTES,
            state_class=SensorStateClass.MEASUREMENT,
            requires_gatt=True,
            value_fn=_daily(index),
        )
        for index in range(7)
    ),
    TaelekSensorEntityDescription(
        key="poll_status",
        translation_key="poll_status",
        device_class=SensorDeviceClass.ENUM,
        options=["pending", "success", "failed"],
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        requires_success=False,
        value_fn=lambda data: (
            "success" if data.gatt else "failed" if data.poll_error else "pending"
        ),
    ),
    TaelekSensorEntityDescription(
        key="last_poll_attempt",
        translation_key="last_poll_attempt",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        requires_success=False,
        value_fn=lambda data: data.last_poll_attempt,
    ),
    TaelekSensorEntityDescription(
        key="last_polled",
        translation_key="last_polled",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_gatt=True,
        value_fn=lambda data: data.last_polled,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: TaelekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Taelek sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        TaelekSensor(coordinator, description)
        for description in SENSORS
        if not description.requires_gatt or coordinator.active_polling
    )


class TaelekSensor(TaelekEntity, SensorEntity):
    """Representation of one decoded advertisement or GATT field."""

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
    def available(self) -> bool:
        """Return whether the entity's own data source has produced data."""
        if self.entity_description.requires_gatt:
            if not self.entity_description.requires_success:
                return self.coordinator.data.last_poll_attempt is not None
            return self.coordinator.data.gatt is not None
        return super().available

    @property
    def native_value(self) -> float | int | str | datetime | None:
        """Return the latest decoded value."""
        data = self.coordinator.data
        if self.entity_description.requires_gatt:
            if self.entity_description.requires_success and data.gatt is None:
                return None
        elif data.advertisement is None:
            return None
        return self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Expose the latest connection error on the polling-status sensor."""
        if self.entity_description.key != "poll_status":
            return None
        if error := self.coordinator.data.poll_error:
            return {"last_error": error}
        return None
