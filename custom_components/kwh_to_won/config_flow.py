"""Config flow for Damda Weather integration."""
from __future__ import annotations

from typing import AbstractSet, Any
from tokenize import Number
from urllib.parse import quote_plus, unquote

import voluptuous as vol
from homeassistant.const import CONF_DEVICE_CLASS, CONF_UNIT_OF_MEASUREMENT, UnitOfEnergy
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.selector import selector
from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorDeviceClass

from homeassistant import config_entries, data_entry_flow

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
            
        data_schema = vol.Schema({
            vol.Required('device_name'): str,
            **_option_schema(self.hass)
        })
        
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(data_schema, user_input),
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

    # async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
    #     """Add reconfigure step to allow to reconfigure a config entry."""
    #     errors = {}
    #     if user_input is not None:
    #         return self.async_create_entry(title=user_input['device_name'], data=user_input)
    #     option_list, errors = _option_list(self.hass)
    #     data_schema = {vol.Required('device_name'): str}
    #     for name, required, default, validation in option_list:
    #         if required == "required":
    #             key = (
    #                 vol.Required(name, default)
    #             )
    #         else:
    #             key = (
    #                 vol.Optional(name, default)
    #             )
    #         data_schema[key] = validation
    #     return self.async_show_form(
    #         step_id="user",
    #         data_schema=vol.Schema(data_schema),
    #         errors=errors
    #     )

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow """

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self._config_entry = config_entry  # 로컬 변수로 저장

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle options flow."""
        conf = self._config_entry
        if conf.source == config_entries.SOURCE_IMPORT:
            return self.async_show_form(step_id="init", data_schema=None)

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(_option_schema(self.hass, conf))
        
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(options_schema, user_input or conf.options or conf.data),
        )

def _option_schema(hass: HomeAssistant, config_entry: config_entries.ConfigEntry | None = None):
    """Return the schema for the options."""
    kwh_sensor = _kwh_energy_sensors(hass)
    kwh_sensor.sort()
    
    schema = {
        vol.Required("energy_entity"): selector({"entity": {"include_entities": kwh_sensor}}),
        vol.Required("checkday_config"): selector({
            "select": {
                "options": [{"value": str(k), "label": v} for k, v in CHECKDAY_OPTION.items()],
                "mode": "dropdown"
            }
        }),
        vol.Required("pressure_config"): selector({
            "select": {
                "options": [{"value": k, "label": v} for k, v in PRESSURE_OPTION.items()],
                "mode": "dropdown"
            }
        }),
        vol.Required("bigfam_dc_config"): selector({
            "select": {
                "options": [{"value": str(k), "label": v} for k, v in BIGFAM_DC_OPTION.items()],
                "mode": "dropdown"
            }
        }),
        vol.Required("welfare_dc_config"): selector({
            "select": {
                "options": [{"value": str(k), "label": v} for k, v in WELFARE_DC_OPTION.items()],
                "mode": "dropdown"
            }
        }),
        vol.Optional("forecast_energy_entity"): str,
        vol.Optional("prev_energy_entity"): str,
        vol.Optional("prev2_energy_entity"): str,
        vol.Required("calibration_config"): selector({
            "number": {
                "min": 0,
                "max": 2,
                "step": 0.01,
                "mode": "box"
            }
        }),
    }
    return schema


def _kwh_energy_sensors(hass: HomeAssistant):
    stateClasses = ['total_increasing', 'total']

    kwh_sensor = [
        sensor
        for sensor in hass.states.async_entity_ids("sensor")
        if _attr_filter(hass, sensor, stateClasses)
    ]

    return kwh_sensor


def _attr_filter(hass: HomeAssistant, sensor: str, stateClasses: AbstractSet[str]):
    state = hass.states.get(sensor)

    if '_kwhto_' in sensor:
        return False

    is_unit_valid = state.attributes.get(CONF_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR
    is_device_valid = state.attributes.get(CONF_DEVICE_CLASS) == SensorDeviceClass.ENERGY
    is_state_valid = state.attributes.get('state_class') in stateClasses

    return is_unit_valid and is_device_valid and is_state_valid
