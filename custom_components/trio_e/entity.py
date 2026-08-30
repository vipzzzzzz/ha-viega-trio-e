"""Base entity for the Viega Trio E."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TrioECoordinator


class TrioEEntity(CoordinatorEntity[TrioECoordinator]):
    """Shared device info + naming."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TrioECoordinator, key: str) -> None:
        super().__init__(coordinator)
        info = coordinator.data.info
        mac = info.get("mac_address", "unknown")
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={(CONNECTION_NETWORK_MAC, mac)},
            manufacturer="Viega",
            model=info.get("model", "Multiplex Trio E"),
            name=info.get("name", "Trio E"),
            sw_version=info.get("version"),
            serial_number=info.get("serial"),
            configuration_url=f"http://{info.get('ip')}/" if info.get("ip") else None,
        )
