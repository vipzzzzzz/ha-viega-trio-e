"""Tap switch for the Viega Trio E."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TrioEConfigEntry
from .entity import TrioEEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrioEConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([TrioETapSwitch(entry.runtime_data)])


class TrioETapSwitch(TrioEEntity, SwitchEntity):
    """Open/close the tap at the configured target temperature and flow."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:faucet"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "tap")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.running

    async def async_turn_on(self, **kwargs: Any) -> None:
        flow = self.coordinator.target_flow or 1.0
        await self.coordinator.client.start_flow(
            self.coordinator.target_temperature, flow
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.stop(self.coordinator.target_temperature)
        await self.coordinator.async_request_refresh()
