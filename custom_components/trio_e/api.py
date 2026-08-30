"""Async client for the Viega Multiplex Trio E local HTTP API.

API surface reverse-engineered from the WLAN module (fw 1.0-4.x) and the
homebridge-trio-e plugin. All endpoints live under http://<ip>/api/tlc/<id>/
and speak JSON; writes are application/x-www-form-urlencoded.

Flow values on the wire are 0.0-1.0; this client exposes them the same way
and leaves percentage mapping to the entity layer.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

API_TIMEOUT = aiohttp.ClientTimeout(total=10)


class TrioEError(Exception):
    """Raised when the Trio E cannot be reached or answers garbage."""


class TrioEClient:
    """Minimal async client for one Trio E controller."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        device_id: int = 1,
    ) -> None:
        self._session = session
        self._base = f"http://{host}/api/tlc/{device_id}"
        self._device_id = device_id

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            async with self._session.get(
                f"{self._base}{path}", timeout=API_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                # The module labels JSON responses inconsistently.
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise TrioEError(f"GET {path} failed: {err}") from err

    async def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        try:
            async with self._session.post(
                f"{self._base}{path}", data=data, timeout=API_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise TrioEError(f"POST {path} failed: {err}") from err

    # --- reads -----------------------------------------------------------

    async def get_info(self) -> dict[str, Any]:
        """Device info: name, model, serial, mac_address, temperature, ..."""
        return await self._get("/")

    async def get_state(self) -> dict[str, Any]:
        """Runtime state: {state, progress, set_temperature, function_test}."""
        return await self._get("/state/")

    async def get_popup(self) -> dict[str, Any]:
        """Drain popup: {state: 0|1}."""
        return await self._get("/popup/")

    async def get_quick(self) -> dict[str, Any]:
        """Stored quick program: {temperature, flow, amount}."""
        return await self._get(f"/quick/{self._device_id}/")

    async def get_settings(self) -> dict[str, Any]:
        return await self._get("/settings/")

    # --- writes ----------------------------------------------------------

    async def set_popup(self, open_: bool) -> None:
        await self._post("/popup/", {"state": 1 if open_ else 0})

    async def run_quick(self) -> None:
        """Trigger the stored quick program (also arms the valve before a
        manual flow start - mirrors homebridge behaviour)."""
        await self._post(f"/quick/{self._device_id}/", {"data": 1})

    async def set_tlc(self, temperature: float, flow: float, changed: bool) -> None:
        """Set mixed-water temperature (degC) and flow (0.0-1.0).

        changed=True while adjusting an open tap / starting, False to stop.
        """
        await self._post(
            "/",
            {
                "temperature": temperature,
                "flow": flow,
                "changed": 1 if changed else 0,
            },
        )

    async def start_flow(self, temperature: float, flow: float) -> None:
        """Open the tap at temperature/flow. The quick trigger first is the
        documented-by-practice arming quirk from homebridge-trio-e."""
        await self.run_quick()
        await self.set_tlc(temperature, flow, True)

    async def stop(self, temperature: float) -> None:
        """Close the tap (also cancels a running volume fill)."""
        await self.set_tlc(temperature, 0, False)

    async def fill_bathtub(self, temperature: float, amount: float) -> None:
        """Volume-based fill: device stops itself at `amount` litres."""
        await self._post(
            "/bathtub-fill/", {"temperature": temperature, "amount": amount}
        )
