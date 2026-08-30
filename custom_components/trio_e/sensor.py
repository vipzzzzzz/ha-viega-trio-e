"""Sensors for the Viega Trio E."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TrioEConfigEntry
from .entity import TrioEEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrioEConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [TrioETemperatureSensor(coordinator), TrioEProgressSensor(coordinator)]
    )


class TrioETemperatureSensor(TrioEEntity, SensorEntity):
    """Live mixed-water temperature at the sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "water_temperature")

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.info.get("temperature")
        return float(value) if isinstance(value, (int, float)) else None


class TrioEProgressSensor(TrioEEntity, SensorEntity):
    """Progress of a volume-based fill (0-100%)."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:waves-arrow-up"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "fill_progress")

    @property
    def native_value(self) -> int | None:
        value = self.coordinator.data.state.get("progress")
        return int(value) if isinstance(value, (int, float)) else None

    @property
    def extra_state_attributes(self) -> dict:
        state = self.coordinator.data.state
        return {
            "raw_state": state.get("state"),
            "set_temperature": state.get("set_temperature"),
        }
