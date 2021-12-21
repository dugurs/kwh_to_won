"""Config flow for Damda Weather integration."""
from __future__ import annotations
from urllib.parse import quote_plus, unquote
from homeassistant.const import CONF_NAME
import voluptuous as vol
from homeassistant.core import callback

from homeassistant import config_entries

from .const import DOMAIN, BIGFAM_DC_OPTION, WELFARE_DC_OPTION, PRESSURE_OPTION

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required('device_name', default="Home"): str,
        vol.Required('energy_entity'): str,
        vol.Required("checkday_config", default=0): int,
        vol.Required("pressure_config", default="low"): vol.In(PRESSURE_OPTION),
        vol.Required("bigfam_dc_config", default=0): vol.In(BIGFAM_DC_OPTION),
        vol.Required("welfare_dc_config", default=0): vol.In(WELFARE_DC_OPTION)
    }
)


OPTION_LIST = [
    ("energy_entity", "", str),
    ("checkday_config", "0", int),
    ("pressure_config", "low", vol.In(PRESSURE_OPTION)),
    ("bigfam_dc_config", "0", vol.In(BIGFAM_DC_OPTION)),
    ("welfare_dc_config", "0", vol.In(WELFARE_DC_OPTION))
]

def make_unique(i):
    """Make unique_id."""
    return f"{i['energy_entity']}_{i['checkday_config']}_{i['pressure_config']}_{i['bigfam_dc_config']}_{i['welfare_dc_config']}"


def check_key(i):
    """Check input data is valid and return data."""
    i_key = i['device_name'].strip()
    k_dec = unquote(i_key)
    if i_key == k_dec:
        i['device_name'] = quote_plus(i_key)
    return i


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Damda Weather."""

    VERSION = "0.0.5"

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            user_input = check_key(user_input)
            await self.async_set_unique_id(make_unique(user_input))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input['device_name'], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Handle a option flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Damda Pad."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        conf = self.config_entry
        if conf.source == config_entries.SOURCE_IMPORT:
            return self.async_show_form(step_id="init", data_schema=None)
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = {}
        data_list = ['energy_entity', 'checkday_config', 'pressure_config', 'bigfam_dc_config', 'welfare_dc_config']
        for name, default, validation in OPTION_LIST:
            to_default = conf.options.get(name, default)
            if name in data_list and conf.options.get(name, default) == default:
                to_default = conf.data.get(name, default)
            key = (
                vol.Required(name, default=to_default)
            )
            options_schema[key] = validation
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(options_schema)
        )