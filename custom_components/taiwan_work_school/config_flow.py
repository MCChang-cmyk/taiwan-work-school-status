"""UI configuration and options."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CITIES, CONF_CITIES, CONF_COUNT, CONF_INTERVAL, CONF_MODE, DEFAULTS, DOMAIN, NAME
from .schedule import evening_minutes


def schema(defaults):
    return vol.Schema(
        {
            vol.Required(
                CONF_CITIES, default=defaults.get(CONF_CITIES, [])
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[{"value": key, "label": name} for key, name in CITIES.items()],
                    multiple=True,
                )
            ),
            vol.Required(CONF_MODE, default=defaults[CONF_MODE]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["hourly", "evening"], translation_key="update_mode"
                )
            ),
            vol.Required(CONF_INTERVAL, default=defaults[CONF_INTERVAL]): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=15)
            ),
            vol.Required(CONF_COUNT, default=defaults[CONF_COUNT]): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=16)
            ),
        }
    )


def validate(data):
    if not data[CONF_CITIES] or any(city not in CITIES for city in data[CONF_CITIES]):
        return {CONF_CITIES: "select_city"}
    if data[CONF_MODE] == "evening":
        try:
            evening_minutes(data[CONF_INTERVAL], data[CONF_COUNT])
        except ValueError:
            return {"base": "window_exceeded"}
    return {}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors = {}
        if user_input is not None:
            errors = validate(user_input)
            if not errors:
                return self.async_create_entry(title=NAME, data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=schema({**DEFAULTS, **(user_input or {})}), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = validate(user_input)
            if not errors:
                return self.async_create_entry(title="", data=user_input)
        defaults = {
            **DEFAULTS,
            **self.config_entry.data,
            **self.config_entry.options,
            **(user_input or {}),
        }
        return self.async_show_form(step_id="init", data_schema=schema(defaults), errors=errors)
