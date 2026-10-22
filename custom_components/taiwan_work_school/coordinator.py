"""One HTTP request feeds every selected county."""

from __future__ import annotations

import asyncio
import logging
import ssl
from datetime import datetime, time, timedelta

import aiohttp
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_COUNT, CONF_INTERVAL, CONF_MODE, NAME, SOURCE_URL, TAIPEI
from .parser import ParseError, Report, parse_html
from .schedule import next_evening_update
from .tls import dgpa_compatibility_context

_LOGGER = logging.getLogger(__name__)


class WorkSchoolCoordinator(DataUpdateCoordinator[Report]):
    def __init__(self, hass, entry, settings):
        super().__init__(hass, _LOGGER, name=NAME, config_entry=entry)
        self.settings = settings
        self.fetched_at: datetime | None = None
        self.next_update: datetime | None = None
        self._cancel_update = None
        self._cancel_midnight = None
        self._stopped = False
        self._dgpa_ssl_context: ssl.SSLContext | None = None

    async def _async_update_data(self):
        try:
            async with asyncio.timeout(30):
                try:
                    html = await self._fetch_html()
                except aiohttp.ClientConnectorCertificateError as err:
                    # OpenSSL 86: legacy CA lacks Subject Key Identifier. Other
                    # failures (expiry, unknown issuer, wrong host) still fail.
                    if (
                        self._dgpa_ssl_context is not None
                        or err.host != "www.dgpa.gov.tw"
                        or err.port != 443
                        or getattr(err.certificate_error, "verify_code", None) != 86
                    ):
                        raise
                    self._dgpa_ssl_context = await self.hass.async_add_executor_job(
                        dgpa_compatibility_context
                    )
                    _LOGGER.warning(
                        "DGPA certificate chain is missing Subject Key Identifier; "
                        "using a site-specific compatibility context with CA and hostname verification"
                    )
                    html = await self._fetch_html()
                report = await self.hass.async_add_executor_job(parse_html, html)
        except (aiohttp.ClientError, TimeoutError, UnicodeError, ParseError) as err:
            raise UpdateFailed(f"Unable to read DGPA announcements: {err}") from err
        self.fetched_at = dt_util.utcnow()
        return report

    async def _fetch_html(self):
        # Do not carry the compatibility context to another host via redirects.
        async with async_get_clientsession(self.hass).get(
            SOURCE_URL, ssl=self._dgpa_ssl_context, allow_redirects=False
        ) as response:
            response.raise_for_status()
            if 300 <= response.status < 400:
                raise UpdateFailed("Unexpected redirect from DGPA announcement URL")
            return await response.text(encoding="utf-8-sig")

    @callback
    def start(self):
        self._schedule_update()
        self._schedule_midnight()
        self.async_update_listeners()

    @callback
    def _schedule_update(self):
        if self._stopped:
            return
        now = dt_util.utcnow()
        self.next_update = (
            now + timedelta(hours=1)
            if self.settings[CONF_MODE] == "hourly"
            else next_evening_update(now, self.settings[CONF_INTERVAL], self.settings[CONF_COUNT])
        )
        self._cancel_update = async_track_point_in_utc_time(
            self.hass, self._scheduled_update, self.next_update
        )

    async def _scheduled_update(self, _now):
        self._cancel_update = None
        # Arm the next timer first so failure or cancellation never loses the schedule.
        self._schedule_update()
        await self.async_refresh()

    @callback
    def _schedule_midnight(self):
        if self._stopped:
            return
        tomorrow = dt_util.utcnow().astimezone(TAIPEI).date() + timedelta(days=1)
        when = datetime.combine(tomorrow, time.min, TAIPEI)
        self._cancel_midnight = async_track_point_in_utc_time(self.hass, self._midnight, when)

    @callback
    def _midnight(self, _now):
        self._cancel_midnight = None
        self._schedule_midnight()
        self.async_update_listeners()

    @callback
    def stop(self):
        self._stopped = True
        for cancel in (self._cancel_update, self._cancel_midnight):
            if cancel:
                cancel()
        self._cancel_update = self._cancel_midnight = None
