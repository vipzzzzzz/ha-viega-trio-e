"""Number entities for the Viega Trio E (target temperature, flow)."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MAX_TEMP, MIN_TEMP
from .coordinator import TrioEConfigEntry
from .entity import TrioEEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrioEConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [TrioETargetTemperature(coordinator), TrioEFlow(coordinator)]
    )


class TrioETargetTemperature(TrioEEntity, NumberEntity):
    """Target mixed-water temperature.

    The module has no persistent setpoint; HA keeps the target and sends it
    with every command. If water is running, changing this re-commands the
    tap immediately.
    """

    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = MIN_TEMP
    _attr_native_max_value = MAX_TEMP
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-water"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "target_temperature")

    @property
    def native_value(self) -> float:
        return self.coordinator.target_temperature

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.target_temperature = value
        if self.coordinator.data.running:
            await self.coordinator.client.set_tlc(
                value, self.coordinator.target_flow, True
            )
        self.async_write_ha_state()


class TrioEFlow(TrioEEntity, NumberEntity):
    """Tap flow in percent. Only commands the device while water is running;
    otherwise it just sets what the tap switch will open with."""

    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "flow")

    @property
    def native_value(self) -> float:
        return round(self.coordinator.target_flow * 100)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.target_flow = value / 100
        if self.coordinator.data.running:
            if value == 0:
                await self.coordinator.client.stop(
                    self.coordinator.target_temperature
                )
            else:
                await self.coordinator.client.set_tlc(
                    self.coordinator.target_temperature, value / 100, True
                )
            await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
