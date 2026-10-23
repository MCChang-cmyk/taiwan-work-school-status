"""Manually refresh the shared DGPA announcements."""

from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RefreshButton(hass.data[DOMAIN][entry.entry_id])])


class RefreshButton(ButtonEntity):
    """Remain available after a failed fetch so the user can retry."""

    _attr_has_entity_name = True
    _attr_name = "臺灣停班停課 更新資訊"
    _attr_icon = "mdi:refresh"
    _attr_unique_id = "refresh"

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.entity_id = "button.taiwan_work_school_refresh"

    async def async_press(self):
        # One coordinator request updates every county. Its debouncer prevents
        # repeated clicks from sending a burst of requests to the official site.
        await self.coordinator.async_request_refresh()
        if not self.coordinator.last_update_success:
            raise HomeAssistantError(
                "無法更新停班停課公告，請查看整合日誌後重試。"
            ) from self.coordinator.last_exception
