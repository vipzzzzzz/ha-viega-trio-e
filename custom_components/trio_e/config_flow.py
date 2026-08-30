"""Config flow for the Viega Trio E integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TrioEClient, TrioEError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class TrioEConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow: just a host, validated live."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = TrioEClient(
                async_get_clientsession(self.hass), user_input[CONF_HOST]
            )
            try:
                info = await client.get_info()
            except TrioEError:
                errors["base"] = "cannot_connect"
            else:
                mac = info.get("mac_address")
                if not mac:
                    errors["base"] = "invalid_device"
                else:
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=info.get("name", "Trio E"), data=user_input
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
