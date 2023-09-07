"""Config flow for Damda Weather integration."""
from __future__ import annotations
from tokenize import Number
from urllib.parse import quote_plus, unquote
from homeassistant.const import CONF_NAME, CONF_DEVICE_CLASS, DEVICE_CLASS_ENERGY, CONF_UNIT_OF_MEASUREMENT, ENERGY_KILO_WATT_HOUR
import voluptuous as vol
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from homeassistant import config_entries

from .const import DOMAIN, CHECKDAY_OPTION, BIGFAM_DC_OPTION, WELFARE_DC_OPTION, PRESSURE_OPTION

# import logging
# _LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Damda Weather."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title=user_input['device_name'], data=user_input)
            
        option_list, errors = _option_list(self.hass)
        data_schema = {vol.Required('device_name'): str}
        for name, required, default, validation in option_list:
            if required == "required":
                key = (
                    vol.Required(name, default=default)
                )
            else:
                key = (
                    vol.Optional(name, default=default)
                )
            data_schema[key] = validation
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors
        )

    async def async_step_import(self, user_input=None):
        """Handle configuration by yaml file."""
        await self.async_set_unique_id(user_input['device_name'])
        for entry in self._async_current_entries():
            if entry.unique_id == self.unique_id:
                self.hass.config_entries.async_update_entry(entry, data=user_input)
                self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input['device_name'], data=user_input)

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
        errors = {}

        conf = self.config_entry
        if conf.source == config_entries.SOURCE_IMPORT:
            return self.async_show_form(step_id="init", data_schema=None)
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        option_list, errors = _option_list(self.hass, conf.data.get('device_name'))
        options_schema = {}
        for name, required, default, validation in option_list:
            to_default = conf.options.get(name, conf.data.get(name, default))
            if required == "required":
                key = (
                    vol.Required(name, default=to_default)
                )
            else:
                key = (
                    vol.Optional(name, default=to_default)
                )
            options_schema[key] = validation
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options_schema),
            errors=errors
        )

def _option_list(hass: HomeAssistant, device_name=None):
    errors = {}
    kwh_sensor = _kwh_energy_sensors(hass, ['total_increasing'])
    if len(kwh_sensor) == 0:
        errors['energy_entity'] = 'entity_not_found'
    kwh_sensor.sort()
    
    kwh_sensor2 = _kwh_energy_sensors(hass, ['total'])
    if len(kwh_sensor2) == 0:
        errors['prev_energy_entity'] = 'prev_entity_not_found'
    kwh_sensor2.sort()
    kwh_sensor21 = kwh_sensor2[:]
    kwh_sensor21.insert(0,"사용 안함")
    kwh_sensor2.insert(0,"내장 예상 사용")

    options = [
        ("energy_entity", "required", "", selector({"entity": {"include_entities": kwh_sensor}})),
        ("checkday_config", "required", 1, vol.In(CHECKDAY_OPTION)),
        ("pressure_config", "required", "low", vol.In(PRESSURE_OPTION)),
        ("bigfam_dc_config", "required", 0, vol.In(BIGFAM_DC_OPTION)),
        ("welfare_dc_config", "required", 0, vol.In(WELFARE_DC_OPTION)),
        ("forecast_energy_entity", "required", "내장 예상 사용", vol.In(kwh_sensor2)),
        ("prev_energy_entity", "required", "사용 안함", vol.In(kwh_sensor21)),
        ("calibration_config", "required", 1, vol.All(vol.Coerce(float), vol.Range(min=0, max=2)))
    ]
    return [options, errors]

def _kwh_energy_sensors(hass: HomeAssistant, stateClass):
    kwh_sensor = [
        senosr
        for senosr in hass.states.async_entity_ids("sensor")
        if _attr_filter(hass, senosr, stateClass)
    ]
    return kwh_sensor if len(kwh_sensor) else []

def _attr_filter(hass: HomeAssistant, sensor: str, stateClass):
    state = hass.states.get(sensor)
    if '_kwhto_' in sensor:
        return False
    return state.attributes.get(CONF_UNIT_OF_MEASUREMENT) == ENERGY_KILO_WATT_HOUR and state.attributes.get(CONF_DEVICE_CLASS) == DEVICE_CLASS_ENERGY and state.attributes.get('state_class') in stateClass

