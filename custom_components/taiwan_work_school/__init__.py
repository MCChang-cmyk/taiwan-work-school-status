"""Taiwan DGPA work and school suspension integration."""

from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er

from .const import CONF_CITIES, DEFAULTS, DOMAIN
from .coordinator import WorkSchoolCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass, entry):
    settings = {**DEFAULTS, **entry.data, **entry.options}
    coordinator = WorkSchoolCoordinator(hass, entry, settings)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    # Retire the separate work/school entities and remove deselected counties.
    registry = er.async_get(hass)
    active_ids = {
        f"{city}:{suffix}"
        for city in settings[CONF_CITIES]
        for suffix in ("announcement", "today:combined", "tomorrow:combined")
    }
    active_ids.add("refresh")
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id not in active_ids:
            registry.async_remove(entity.entity_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.start()
    entry.async_on_unload(coordinator.stop)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id).stop()
    return unloaded
