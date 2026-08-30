"""Drain popup valve for the Viega Trio E."""

from __future__ import annotations

from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TrioEConfigEntry
from .entity import TrioEEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrioEConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([TrioEPopupValve(entry.runtime_data)])


class TrioEPopupValve(TrioEEntity, ValveEntity):
    """The bathtub drain popup: open = water drains."""

    _attr_device_class = ValveDeviceClass.WATER
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    _attr_reports_position = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "popup")

    @property
    def is_closed(self) -> bool | None:
        state = self.coordinator.data.popup.get("state")
        if state is None:
            return None
        return state == 0

    async def async_open_valve(self) -> None:
        await self.coordinator.client.set_popup(True)
        await self.coordinator.async_request_refresh()

    async def async_close_valve(self) -> None:
        await self.coordinator.client.set_popup(False)
        await self.coordinator.async_request_refresh()
