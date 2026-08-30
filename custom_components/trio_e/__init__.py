"""The Viega Trio E integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TrioEClient, TrioEError
from .const import (
    ATTR_TEMPERATURE,
    ATTR_VOLUME,
    DOMAIN,
    MAX_TEMP,
    MIN_TEMP,
    SERVICE_FILL_BATH,
)
from .coordinator import TrioEConfigEntry, TrioECoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

FILL_BATH_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TEMPERATURE): vol.All(
            vol.Coerce(float), vol.Range(min=MIN_TEMP, max=MAX_TEMP)
        ),
        vol.Required(ATTR_VOLUME): vol.All(
            vol.Coerce(float), vol.Range(min=1, max=2000)
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register domain services."""

    async def _fill_bath(call: ServiceCall) -> None:
        loaded = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.state is ConfigEntryState.LOADED
        ]
        if not loaded:
            raise HomeAssistantError("No Trio E is configured/loaded")
        coordinator = loaded[0].runtime_data
        try:
            await coordinator.client.fill_bathtub(
                call.data[ATTR_TEMPERATURE], call.data[ATTR_VOLUME]
            )
        except TrioEError as err:
            raise HomeAssistantError(f"Trio E fill failed: {err}") from err
        coordinator.target_temperature = call.data[ATTR_TEMPERATURE]
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_FILL_BATH, _fill_bath, schema=FILL_BATH_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TrioEConfigEntry) -> bool:
    """Set up Trio E from a config entry."""
    client = TrioEClient(async_get_clientsession(hass), entry.data[CONF_HOST])
    coordinator = TrioECoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TrioEConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
