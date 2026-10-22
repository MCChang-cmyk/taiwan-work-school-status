"""County announcement and date-specific work/school sensors."""

from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CITIES, CONF_CITIES, DOMAIN, SOURCE_URL, STATUS_OPTIONS, TAIPEI


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for city in coordinator.settings[CONF_CITIES]:
        entities.append(AnnouncementSensor(coordinator, city))
        for offset in (0, 1):
            entities.append(StatusSensor(coordinator, city, offset))
    async_add_entities(entities)


class CountySensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, city):
        super().__init__(coordinator)
        self.city = city

    @property
    def extra_state_attributes(self):
        report = self.coordinator.data
        return {
            "county": CITIES[self.city],
            "source": SOURCE_URL,
            "report_date": report.report_date.isoformat(),
            "source_updated": report.source_updated.isoformat() if report.source_updated else None,
            "last_successful_fetch": self.coordinator.fetched_at.isoformat()
            if self.coordinator.fetched_at
            else None,
            "next_update": self.coordinator.next_update.isoformat()
            if self.coordinator.next_update
            else None,
            "announcements": list(report.announcements[self.city]),
        }


class AnnouncementSensor(CountySensor):
    _attr_icon = "mdi:bullhorn"

    def __init__(self, coordinator, city):
        super().__init__(coordinator, city)
        self._attr_unique_id = f"{city}:announcement"
        self._attr_name = f"{CITIES[city]} 停班停課公告"
        self.entity_id = f"sensor.taiwan_work_school_{city}_announcement"

    @property
    def native_value(self):
        text = "；".join(self.coordinator.data.announcements[self.city]) or "尚未宣布訊息"
        return text if len(text) <= 255 else text[:254] + "…"


class StatusSensor(CountySensor):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _attr_translation_key = "suspension_status"

    def __init__(self, coordinator, city, offset):
        super().__init__(coordinator, city)
        self.offset = offset
        day = "today" if offset == 0 else "tomorrow"
        self._attr_unique_id = f"{city}:{day}:combined"
        self.entity_id = f"sensor.taiwan_work_school_{city}_{day}"
        self._attr_name = f"{CITIES[city]} {'今天' if offset == 0 else '明天'}停班停課"
        self._attr_icon = "mdi:weather-hurricane"

    @property
    def target_date(self):
        return dt_util.utcnow().astimezone(TAIPEI).date() + timedelta(days=self.offset)

    @property
    def native_value(self):
        return self.coordinator.data.combined_status(self.city, self.target_date)

    @property
    def extra_state_attributes(self):
        report = self.coordinator.data
        target = self.target_date
        return {
            **super().extra_state_attributes,
            "target_date": target.isoformat(),
            "work_status": report.status(self.city, target, "上班"),
            "school_status": report.status(self.city, target, "上課"),
        }
