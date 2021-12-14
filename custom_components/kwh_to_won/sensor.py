"""Platform for sensor integration."""
# This file shows the setup for the sensors associated with the cover.
# They are setup in the same way with the call to the async_setup_entry function
# via HA from the module __init__. Each sensor has a device_class, this tells HA how
# to display it in the UI (for know types). The unit_of_measurement property tells HA
# what the unit is, so it can display the correct range. For predefined types (such as
# battery), the unit_of_measurement should match what's expected.
import random
import logging
import time
import homeassistant
from typing import Optional
from homeassistant.const import (
    DEVICE_CLASS_BATTERY,
    PERCENTAGE,
    DEVICE_CLASS_ILLUMINANCE,
    ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT, CONF_ICON_TEMPLATE,
    CONF_ENTITY_PICTURE_TEMPLATE, CONF_SENSORS, EVENT_HOMEASSISTANT_START,
    MATCH_ALL, CONF_DEVICE_CLASS, STATE_UNKNOWN,
    STATE_UNAVAILABLE, ATTR_TEMPERATURE, TEMP_FAHRENHEIT,
    CONF_UNIQUE_ID, DEVICE_CLASS_ENERGY, ENERGY_KILO_WATT_HOUR
)
from homeassistant.components.sensor import ENTITY_ID_FORMAT, \
    PLATFORM_SCHEMA, DEVICE_CLASSES_SCHEMA

from homeassistant.const import ATTR_VOLTAGE
import asyncio

from homeassistant import components
from homeassistant import util
from homeassistant.helpers.entity import Entity
from .const import DOMAIN, VERSION, MANUFACTURER, MODEL, CALC_PARAMETER
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.event import async_track_state_change

import locale
import math
import datetime

D = datetime.datetime.now()

_LOGGER = logging.getLogger(__name__)

# 센서명, 클래스, 단위, 아이콘
SENSOR_TYPES = {
    'kwh2won': ['전기 사용요금', None, '₩', 'mdi:cash-usd'],
    'forecast': ['전기 예상사용량', DEVICE_CLASS_ENERGY, ENERGY_KILO_WATT_HOUR, 'mdi:counter'],
    'forecast_kwh2won': ['전기 예상요금', None, '₩', 'mdi:cash-usd'],
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
        self._device_state_attributes = {}
        self._icon = None
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

        async_track_state_change(
            self.hass, self._energy_entity, self.energy_state_listener)

        energy_state = hass.states.get(energy_entity)
        if _is_valid_state(energy_state):
            # self._energy = math.floor(float(energy_state.state)*10)/10 # kwh 소수 1자리 이하 버림
            self._energy = float(energy_state.state)


    def energy_state_listener(self, entity, old_state, new_state):
        """Handle temperature device state changes."""
        if _is_valid_state(new_state):
            self._energy = util.convert(new_state.state, float)
            # self._energy = math.floor(float(new_state.state)*10)/10 # kwh 소수 1자리 이하 버림
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
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._device_state_attributes

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
            self._energy_forecast = self.energy_forecast(self._energy, self._checkday)
            self._state = self._energy_forecast
        else :
            if self._sensor_type == "kwh2won":
                self._total_charge = self.kwh2won(self._energy)
                self._device_state_attributes['전기사용량'] = self._energy
            else:
                self._energy_forecast = self.energy_forecast(self._energy, self._checkday)
                self._total_charge = self.kwh2won(self._energy_forecast)
                self._device_state_attributes['전기예상사용량'] = self._energy_forecast
            self._state = self._total_charge
            self._device_state_attributes['검침일'] = self._checkday
            self._device_state_attributes['사용용도'] = self._pressure
            self._device_state_attributes['대가족_할인'] = self._bigfam_dc
            self._device_state_attributes['복지_할인'] = self._welfare_dc
            self._device_state_attributes['누진단계_상'] = self._prog_up
            self._device_state_attributes['누진단계_하'] = self._prog_down

    async def async_update(self):
        """Update the state."""
        self.update()


    # 예상 사용량
    def energy_forecast(self, energy, checkday):
        # 사용일 = (오늘 > 검침일) ? 오늘 - 검침일 : 전달일수 - 검침일 + 오늘
        # 월일수 = (오늘 > 검침일) ? 이번달일수 : 전달일수
        # 시간나누기 = ((사용일-1)*24)+(현재시간+1)
        # 시간곱하기 = 월일수*24
        # 예측 = 에너지 / 시간나누기 * 시간곱하기
        if D.day == checkday :
            return round(energy, 1)
        elif D.day > checkday :
            lastday = self.last_day_of_month(datetime.date(D.year, D.month, 1))
            lastday = lastday.day
            useday = D.day - checkday
        else :
            lastday = D - datetime.timedelta(days=D.day)
            lastday = lastday.day
            useday = lastday + D.day - checkday
        return round(energy / (((useday - 1) * 24) + D.hour + 1) * (lastday * 24), 1)

    # 달의 말일
    # last_day_of_month(datetime.date(2021, 12, 1))
    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)


    # 누진 요금 구하기
    def prog_calc(self, energy,kwhprice,kwhsection):
        won = 0
        section = 0
        for s in [2,1,0]:
            if kwhsection[s] < energy : # 상계금액
                # print(f'{s+1}단계 금액 : {(energy - kwhsection[s]) * kwhprice[s]}won = {energy - kwhsection[s]}kWh * {kwhprice[s]}won, energy: {energy}')
                won += (energy - kwhsection[s]) * kwhprice[s] # 구간 요금 계산
                energy -= energy - kwhsection[s] # 계산된 구간 용량 빼기
                section += 1 # 누진 단계
        return {'won':won, 'section':section}

    def kwh2won(self,energy) :
        # d = new Date()
        monthday = (D.month * 100) + D.day
        # monthday = 710
        checkday = self._checkday # 검침일

        # basicprice = [910, 1600, 7300] # 기본요금(원/호)
        # kwhprice = [88.3, 182.9, 275.6] # 전력량 요금(원/kWh)
        # # kwhprice = [93.3, 187.9, 280.6] # 전력량 요금(원/kWh) - 개편전 요금
        # kwhsectionUp = [0, 200, 400] # 구간(kWh - 상계)
        # kwhsectionDown = [0, 300, 450] # 구간(kWh - 하계)(7~8월)
        # adjustment = [-5, 5.3, 0] # 환경비용차감 + 기후환경요금 + 연료비조정액
        # # adjustment = [-5, 5.3, -3] # 환경비용차감 + 기후환경요금 + 연료비조정액 - 개편전 요금
        pressure = self._pressure # 저압 'low', 고압 'high'
        basicprice = CALC_PARAMETER[pressure]['basicprice'] # 기본요금(원/호)
        kwhprice = CALC_PARAMETER[pressure]['kwhprice'] # 전력량 요금(원/kWh)
        kwhsectionUp = CALC_PARAMETER[pressure]['kwhsectionUp'] # 구간(kWh - 상계)
        kwhsectionDown = CALC_PARAMETER[pressure]['kwhsectionDown'] # 구간(kWh - 하계)(7~8월)
        adjustment = CALC_PARAMETER[pressure]['adjustment'] # 환경비용차감 + 기후환경요금 + 연료비조정액
        elecBasicLimit = CALC_PARAMETER[pressure]['elecBasicLimit'] # 
        
        dayUp = 0 # 상계일수
        dayDown = 0 # 하계일수 (7,8월)
        DemandUp = 0 # 상계 전력량요금
        DemandDown = 0 # 하계 전력량요금
        progUp = 0 # 누진단계
        progDown = 0
        # BasicCharge = 0 # 기본요금
        UsingCharge = 0 # 전력량요금
        totalCharge = 0 # 최종금액

        # 검침일이 말일일때
        if checkday == 0 :
            lastdate = self.last_day_of_month(datetime.date(D.year, D.month, 1))
            checkday = lastdate.day

        adjustValue = math.floor(energy * (adjustment[0] + adjustment[1] + adjustment[2])) # 조정액
        # print(f'energy {energy}')
        # print(f'조정액 {adjustValue} = {adjustment[0]} + {adjustment[1]} + {adjustment[2]}')
        # print(f'월일 {monthday}, 검침일 {checkday}')

        # 누진 계산
        # 상계요금
        prog = self.prog_calc(energy,kwhprice,kwhsectionUp)
        DemandUp = prog['won']
        progUp = prog['section']
        self._prog_up = progUp
        # print(f'상계 요금 : {basicprice[progUp-1]+DemandUp}원 = {progUp}단계, 기본 {basicprice[progUp-1]}원 + 사용 {DemandUp}원')
        DemandUp += basicprice[progUp-1] # 기본요금 더하기

        if (monthday > checkday + 600) and (monthday <= checkday + 900) : # 하계(7~8월), 상하계 사용 일수 계산
            # 하계요금
            prog = self.prog_calc(energy,kwhprice,kwhsectionDown)
            DemandDown = prog['won']
            progDown = prog['section']
            self._prog_down = progDown
            # print(f'하계 요금 : {basicprice[progDown-1]+DemandDown}원 = {progDown}단계, 기본 {basicprice[progDown-1]}원 + 사용 {DemandDown}원')
            DemandDown += basicprice[progDown-1]

            if monthday <= checkday + 700 : # 검침일이 7월일때 
                dayUp = 30 - checkday
                dayDown = checkday
            elif monthday <= checkday + 800 : # 검침일이 8월일때 
                dayUp = 0
                dayDown = 31
            else : # 검침일이 9월일때 
                dayUp = checkday
                dayDown = 31 - checkday
            # print(f'상계 일수 {dayUp}일, 일계요금 {math.floor(DemandUp * dayUp / (dayUp+dayDown))}')
            # print(f'하계 일수 {dayDown}일, 일계요금 {math.floor(DemandDown * dayDown / (dayUp+dayDown))}')
            UsingCharge = math.floor(DemandUp * dayUp / (dayUp+dayDown)) + math.floor(DemandDown * dayDown / (dayUp+dayDown))
        else : # 상계
            # print(f'상계 일수 *일, 일계요금 {DemandUp}원')
            # print(f'하계 일수 0일, 일계요금 0원')
            UsingCharge = DemandUp

        iBigFamBoolean = self._bigfam_dc # 대가족 요금할인
        iWelfareDcBoolean = self._welfare_dc # 복지 요금할인

        dcValue = 0 # 최종 할인요금
        elecBasicValue = 0 # 필수사용량 보장공제
        elecBasic200Value = 0 # 200kWh 이하 감액

        # 필수사용량 보장공제
        # 가정용 저압 [200kWh 이하, 최대 2,000원]
        # 가정용 고압, 복지할인시 [200kWh 이하, 2,500원]
        # (기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) - 1000
        elecBasic = 200
        if (energy <= elecBasic) :
            elecBasicValue = UsingCharge + adjustValue - 1000
            if elecBasicValue > elecBasicLimit :
                elecBasicValue = elecBasicLimit
                # print(f'필수사용량 보장공제 : {elecBasicValue}')


        if (iBigFamBoolean or iWelfareDcBoolean) :
            # 복지할인
            # 필수사용량 보장공제 = 0
            # 200kWh 이하 감액(원미만 절사) = 저압 4,000  고압 2,500
            if (energy <= elecBasic) :
                elecBasicValue = 0
                elecBasic200Value = UsingCharge + adjustValue
                if elecBasic200Value > elecBasic200Limit :
                    elecBasic200Value = elecBasic200Limit
                # print(f'200kWh 이하 감액 : {elecBasic200Value}')

            # 복지 요금할인
            # B1 : 독립유공자,국가유공자,5.18민주유공자,장애인 (16,000원 한도)
            # B2 : 사회복지시설 (전기요금계((기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액) － 필수사용량 보장공제) x 30%, 한도 없음)
            # B3 : 기초생활(생계.의료) (16,000원 한도) + 중복할인
            # B4 : 기초생활(주거.교육) (10,000원 한도) + 중복할인
            # B5 : 차사위계층 (8,000원 한도) + 중복할인
            # B  : 전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액 － 200kWh이하감액 － 복지할인)
            # B2 :              전기요금계(기본요금 ＋ 전력량요금 ＋ 기후환경요금 ± 연료비조정액 － 200kWh이하감액 － 복지할인 － 필수사용량 보장공제)
            iWelfareDcValue = 0
            if (iWelfareDcBoolean) :
                iWelfareDcValue = math.floor(UsingCharge + adjustValue)
                if (iWelfareDcBoolean == 1) : # B1
                    if (iWelfareDcValue > 16000) :
                        iWelfareDcValue = 16000
                    # print(f'유공자,장애인 : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or 16,000')
                elif (iWelfareDcBoolean == 2) :
                    iWelfareDcValue = math.floor((UsingCharge + adjustValue) * 0.3)
                    # print(f'사회복지시설 : {iWelfareDcValue} = (전기요금계 - 필수사용량 보장공제 ) x 30%, 한도 없음')
                elif (iWelfareDcBoolean == 3) :
                    if (iWelfareDcValue > 16000) :
                        iWelfareDcValue = 16000
                    # print(f'기초생활(생계.의료) : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or 16,000')
                elif (iWelfareDcBoolean == 4) :
                    if (iWelfareDcValue > 10000) :
                        iWelfareDcValue = 10000
                    # print(f'기초생활(주거.교육) : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or 10,000')
                elif (iWelfareDcBoolean == 5) :
                    if (iWelfareDcValue > 8000) :
                        iWelfareDcValue = 8000
                    # print(f'차사위계층 : {iWelfareDcValue} = (전기요금계 - 200kWh이하감액 ) or 8,000')

            # 대가족 요금할인
            # A1 : 5인이상 가구,출산가구,3자녀이상 가구 (16,000원 한도)
            # A2 : 생명유지장치 (한도 없음)
            # 전기요금계((기본요금 ＋ 전력량요금 － 필수사용량 보장공제 ＋ 기후환경요금 ± 연료비조정액) － 200kWh이하감액) x 30% = 대가족 요금할인
            iBigFamValue = 0
            if (iBigFamBoolean) :
                iWelfareDcValue_temp = 0
                if (iWelfareDcBoolean >= 2) : # A2
                    iWelfareDcValue_temp = iWelfareDcValue
                iBigFamValue = math.floor((UsingCharge + adjustValue - elecBasic200Value - iWelfareDcValue_temp) * 0.3)
                if (iBigFamBoolean == 1) : # A1
                    if (iBigFamValue > 16000) :
                        iBigFamValue = 16000
                    # print(f'대가족 요금할인 : {iBigFamValue} = 전기요금계 - {elecBasic200Value} - {iWelfareDcValue_temp} x30%, 최대 16000')
                # else :
                    # print(f'생명유지장치 : {iBigFamValue} = 전기요금계 - {elecBasic200Value} - {iWelfareDcValue_temp} x30%')

            # A B 중 큰 금액 적용
            # 차사위계층,기초생활은 중복할인 (A + B)
            if (iWelfareDcBoolean >= 3) : # 중복할인
                dcValue = iBigFamValue + iWelfareDcValue
                # print(f'복지할인 {dcValue} = 대가족 요금할인 {iBigFamValue} + 복지 요금할인 {iWelfareDcValue}')
            else :
                if (iBigFamValue > iWelfareDcValue) :
                    dcValue = iBigFamValue
                else :
                    dcValue = iWelfareDcValue 
                # print(f'복지할인 {dcValue} = 대가족 요금할인 {iBigFamValue} or 복지 요금할인 {iWelfareDcValue} 더큰것')

        # print(f'최종 요금 : {round((UsingCharge + adjustValue - elecBasicValue - elecBasic200Value - dcValue) * 1.137)}원 = ((사용요금 {UsingCharge} + (조정액 {adjustValue}) - 필수사용량 보장공제{elecBasicValue} - 200kWh 이하 감액{elecBasic200Value} - 복지할인 {dcValue}) * 부가세,기금1.137)')
        totalCharge =  (UsingCharge + adjustValue - elecBasicValue - elecBasic200Value - dcValue) * 1.137

        if (totalCharge < 0) :
            totalCharge = 0
        elif (energy == 0) : # 사용량이 0 이면 50% 할인
            totalCharge = int(totalCharge/2)
        totalCharge =  math.floor(totalCharge/10)*10
        return totalCharge


def _is_valid_state(state) -> bool:
    return state and state.state != STATE_UNKNOWN and state.state != STATE_UNAVAILABLE and not math.isnan(float(state.state))
