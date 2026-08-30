"""Buttons for the Viega Trio E (quick program, stop)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    async_add_entities([TrioEQuickButton(coordinator), TrioEStopButton(coordinator)])


class TrioEQuickButton(TrioEEntity, ButtonEntity):
    """Run the quick program stored on the device's front panel."""

    _attr_icon = "mdi:bathtub"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "quick_program")

    @property
    def extra_state_attributes(self) -> dict:
        quick = self.coordinator.data.quick
        return {
            "temperature": quick.get("temperature"),
            "flow": quick.get("flow"),
            "amount": quick.get("amount"),
        }

    async def async_press(self) -> None:
        await self.coordinator.client.run_quick()
        await self.coordinator.async_request_refresh()


class TrioEStopButton(TrioEEntity, ButtonEntity):
    """Stop any running flow or fill immediately."""

    _attr_icon = "mdi:stop-circle-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "stop")

    async def async_press(self) -> None:
        await self.coordinator.client.stop(self.coordinator.target_temperature)
        await self.coordinator.async_request_refresh()
