"""DataUpdateCoordinator for the Viega Trio E."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TrioEClient, TrioEError
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TEMP,
    DOMAIN,
    FAST_SCAN_INTERVAL,
    MAX_TEMP,
    MIN_TEMP,
    STATE_IDLE,
)

_LOGGER = logging.getLogger(__name__)

TrioEConfigEntry = ConfigEntry["TrioECoordinator"]


@dataclass
class TrioEData:
    """Snapshot of everything we poll from the module."""

    info: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    popup: dict[str, Any] = field(default_factory=dict)
    quick: dict[str, Any] = field(default_factory=dict)

    @property
    def running(self) -> bool:
        return self.state.get("state", STATE_IDLE) != STATE_IDLE


class TrioECoordinator(DataUpdateCoordinator[TrioEData]):
    """Polls the Trio E; speeds up while water is running."""

    config_entry: TrioEConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: TrioEConfigEntry, client: TrioEClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        # Target temperature and flow live in HA, not on the device: the
        # module only accepts them per command. Seeded from the device's
        # required_temp on first refresh.
        self.target_temperature: float = DEFAULT_TEMP
        self.target_flow: float = 1.0  # 0.0-1.0
        self._seeded = False

    async def _async_update_data(self) -> TrioEData:
        try:
            info = await self.client.get_info()
            state = await self.client.get_state()
            popup = await self.client.get_popup()
            quick = await self.client.get_quick()
        except TrioEError as err:
            raise UpdateFailed(str(err)) from err

        data = TrioEData(info=info, state=state, popup=popup, quick=quick)

        if not self._seeded:
            seed = info.get("required_temp") or info.get("temperature")
            if isinstance(seed, (int, float)) and MIN_TEMP <= seed <= MAX_TEMP:
                self.target_temperature = float(seed)
            self._seeded = True

        # Poll fast while water is moving so progress/temp track the fill.
        wanted = FAST_SCAN_INTERVAL if data.running else DEFAULT_SCAN_INTERVAL
        if self.update_interval != timedelta(seconds=wanted):
            self.update_interval = timedelta(seconds=wanted)

        return data
