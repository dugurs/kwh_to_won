"""Platform for sensor integration."""
# This file shows the setup for the sensors associated with the cover.
# They are setup in the same way with the call to the async_setup_entry function
# via HA from the module __init__. Each sensor has a device_class, this tells HA how
# to display it in the UI (for know types). The unit_of_measurement property tells HA
# what the unit is, so it can display the correct range. For predefined types (such as
# battery), the unit_of_measurement should match what's expected.
import logging
from typing import Optional
from homeassistant.const import (
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
    CONF_UNIQUE_ID, DEVICE_CLASS_ENERGY, ENERGY_KILO_WATT_HOUR
)
from homeassistant.components.sensor import ENTITY_ID_FORMAT

import asyncio

from homeassistant import util
from homeassistant.helpers.entity import Entity
from .const import DOMAIN, VERSION, MANUFACTURER, MODEL
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.event import async_track_state_change

from .kwh2won_api import NOW, kwh2won_api as K2WAPI
import math

_LOGGER = logging.getLogger(__name__)

# 센서명, 클래스, 단위, 아이콘
SENSOR_TYPES = {
    'kwh2won': ['전기 사용요금', None, '원', 'mdi:cash-100'],
    'forecast': ['전기 예상사용량', DEVICE_CLASS_ENERGY, ENERGY_KILO_WATT_HOUR, 'mdi:counter'],
    'forecast_kwh2won': ['전기 예상요금', None, '원', 'mdi:cash-100'],
}


# See cover.py for more details.
# Note how both entities for each roller sensor (battry and illuminance) are added at
# the same time to the same list. This way only a single async_add_devices call is
# required.
async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""

    device = Device(config_entry.data.get("device_name"))
    energy_entity = config_entry.data.get('energy_entity')
    checkday_config = int(config_entry.data.get('checkday_config'))
    pressure_config = config_entry.data.get('pressure_config')
    bigfam_dc_config = int(config_entry.data.get('bigfam_dc_config'))
    welfare_dc_config = int(config_entry.data.get('welfare_dc_config'))

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                return await api.fetch_data()
        except ApiAuthError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    new_devices = []

    for sensor_type in SENSOR_TYPES:
        new_devices.append(
                ExtendSensor(
                        hass,
                        device,
                        energy_entity,
                        checkday_config,
                        pressure_config,
                        bigfam_dc_config,
                        welfare_dc_config,
                        sensor_type,
                        device.device_id + sensor_type
                        
                )
        )

    if new_devices:
        async_add_devices(new_devices)


# This base class shows the common properties and methods for a sensor as used in this
# example. See each sensor for further details about properties and methods that
# have been overridden.
class SensorBase(Entity):
    """Base representation of a Hello World Sensor."""

    should_poll = False
    
    def __init__(self, device):
        """Initialize the sensor."""
        self._device = device

    # To link this entity to the cover device, this property must return an
    # identifiers value matching that used in the cover, but no other information such
    # as name. If name is returned, this entity will then also become a device in the
    # HA UI.
    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._device.device_id)},
            # If desired, the name for the device could be different to the entity
            "name": self._device.device_id,
            "sw_version": self._device.firmware_version,
            "model": self._device.model,
            "manufacturer": self._device.manufacturer
        }

    # This property is important to let HA know if this entity is online or not.
    # If an entity is offline (return False), the UI will refelect this.
    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return True
        #return self._roller.online and self._roller.hub.online
        
    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        # Sensors should also register callbacks to HA when their state changes
        self._device.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._device.remove_callback(self.async_write_ha_state)


class Device:
    """Dummy roller (device for HA) for Hello World example."""

    def __init__(self, name):
        """Init dummy roller."""
        self._id = name
        self.name = name
        self._callbacks = set()
        self._loop = asyncio.get_event_loop()
        # Reports if the roller is moving up or down.
        # >0 is up, <0 is down. This very much just for demonstration.

        # Some static information about this device
        self.firmware_version = VERSION
        self.model = MODEL
        self.manufacturer = MANUFACTURER

    @property
    def device_id(self):
        """Return ID for roller."""
        return self._id

    def register_callback(self, callback):
        """Register callback, called when Roller changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    # In a real implementation, this library would call it's call backs when it was
    # notified of any state changeds for the relevant device.
    async def publish_updates(self):
        """Schedule call all registered callbacks."""
        for callback in self._callbacks:
            callback()

class ExtendSensor(SensorBase):
    """Representation of a Thermal Comfort Sensor."""

    def __init__(self, hass, device,
                        energy_entity,
                        checkday_config,
                        pressure_config,
                        bigfam_dc_config,
                        welfare_dc_config,
                        sensor_type, unique_id):
        """Initialize the sensor."""
        super().__init__(device)

        self.hass = hass
        self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, "{}_{}".format(device.device_id, sensor_type), hass=hass)
        self._name = "{} {}".format(device.device_id, SENSOR_TYPES[sensor_type][0])
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][2]
        self._state = None
        self._extra_state_attributes = {}
        self._icon = SENSOR_TYPES[sensor_type][3]
        self._device_class = SENSOR_TYPES[sensor_type][1]
        self._sensor_type = sensor_type
        self._unique_id = unique_id
        self._device = device
        self._entity_picture = None
        

        self._energy_entity = energy_entity # energy 엔터티
        self._energy = None
        self._pressure = pressure_config # 저압고압
        self._checkday = checkday_config # 검침일
        self._bigfam_dc = bigfam_dc_config
        self._welfare_dc = welfare_dc_config
        self._total_charge = 0 # 최종금액
        self._prog_up = 0
        self._prog_down = 0
        self._k2h_config = {
            'pressure' : pressure_config,
            'checkday' : checkday_config, # 검침일
            'monthday' : (NOW.month * 100) + NOW.day, # 월일 mmdd
            'bigfam_dc' : bigfam_dc_config, # 대가족 요금할인
            'welfare_dc' : welfare_dc_config, # 복지 요금할인
        }
        self.KWH2WON = K2WAPI(self._k2h_config)

        async_track_state_change(
            self.hass, self._energy_entity, self.energy_state_listener)

        # energy_state = hass.states.get(energy_entity)
        # if _is_valid_state(energy_state):
        #     self._energy = math.floor(float(energy_state.state)*10)/10 # kwh 소수 1자리 이하 버림

    def energy_state_listener(self, entity, old_state, new_state):
        """Handle temperature device state changes."""
        if _is_valid_state(new_state):
            self._energy = util.convert(new_state.state, float)
        self.async_schedule_update_ha_state(True)

    def unique_id(self):
        """Return Unique ID string."""
        return self.unique_id

    """Sensor Properties"""
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._extra_state_attributes

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self._icon

    @property
    def device_class(self) -> Optional[str]:
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def entity_picture(self):
        """Return the entity_picture to use in the frontend, if any."""
        return self._entity_picture

    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the device."""
        return self._unit_of_measurement

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        if self._unique_id is not None:
            return self._unique_id + self._sensor_type

    def update(self):
        """Update the state."""
        
        if self._sensor_type == "forecast":
            self._energy_forecast = self.KWH2WON.energy_forecast(self._energy)
            self._state = self._energy_forecast
        else :
            if self._sensor_type == "kwh2won":
                ret = self.KWH2WON.kwh2won(self._energy)
                self._total_charge = ret['won']
                self._extra_state_attributes['전기사용량'] = self._energy
            else:
                self._energy_forecast = self.KWH2WON.energy_forecast(self._energy)
                ret = self.KWH2WON.kwh2won(self._energy_forecast)
                self._total_charge = ret['won']
                self._extra_state_attributes['전기예상사용량'] = self._energy_forecast
            self._state = self._total_charge
            self._extra_state_attributes['검침일'] = self._checkday
            self._extra_state_attributes['사용용도'] = self._pressure
            self._extra_state_attributes['대가족_할인'] = self._bigfam_dc
            self._extra_state_attributes['복지_할인'] = self._welfare_dc
            self._extra_state_attributes['누진단계_상'] = ret['progUp']
            self._extra_state_attributes['누진단계_하'] = ret['progDown']

    async def async_update(self):
        """Update the state."""
        self.update()


def _is_valid_state(state) -> bool:
    return state and state.state != STATE_UNKNOWN and state.state != STATE_UNAVAILABLE and not math.isnan(float(state.state))
