"""Sensor 플랫폼 통합을 위한 파일입니다."""
import logging
from typing import Optional

# Home Assistant Core에서 필요한 상수 및 클래스를 가져옵니다.
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE, CONF_UNIQUE_ID, UnitOfEnergy
from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorDeviceClass

import asyncio
from homeassistant import util

# Home Assistant 엔티티 및 이벤트 관련 헬퍼 함수를 가져옵니다.
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.core import Event, callback
# async_track_state_change_event: 특정 엔티티의 상태 변경을 감지하는 리스너를 등록합니다.
# async_call_later: 지정된 시간 후에 특정 함수를 실행하도록 예약(스케줄링)합니다. (디바운싱에 사용)
from homeassistant.helpers.event import async_track_state_change_event, async_call_later

# 이 통합 구성요소의 상수 및 API를 가져옵니다.
from .const import DOMAIN, VERSION, MANUFACTURER, MODEL, PRESSURE_OPTION, BIGFAM_DC_OPTION, WELFARE_DC_OPTION
from .kwh2won_api import kwh2won_api as K2WAPI
import math
import datetime
import re # 정규 표현식 모듈

# 로거 설정
_LOGGER = logging.getLogger(__name__)

# 생성할 센서의 종류와 속성을 정의하는 딕셔너리입니다.
# 형식: '센서타입': ['이름', '디바이스 클래스', '단위', '아이콘', '상태 클래스']
SENSOR_TYPES = {
    'kwhto_kwh': ['전기 현재사용량', SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, 'mdi:counter', 'total_increasing'],
    'kwhto_won': ['전기 사용요금', SensorDeviceClass.MONETARY, 'krw', 'mdi:cash-100', 'total_increasing'],
    'kwhto_forecast': ['전기 예상사용량', SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, 'mdi:counter', ''],
    'kwhto_forecast_won': ['전기 예상요금', SensorDeviceClass.MONETARY, 'krw', 'mdi:cash-100', ''],
    'kwhto_won_prev': ['전기 전월 사용요금', SensorDeviceClass.MONETARY, 'krw', 'mdi:cash-100', 'total'],
    'kwhto_won_prev2': ['전기 전전월 사용요금', SensorDeviceClass.MONETARY, 'krw', 'mdi:cash-100', 'total'],
}

async def async_setup_entry(hass, config_entry, async_add_devices):
    """config_entry를 기반으로 센서를 설정하고 Home Assistant에 추가합니다."""

    # 사용자가 설정한 기기 이름을 기반으로 부모 디바이스 객체를 생성합니다.
    device = Device(config_entry.data.get("device_name"))

    # 사용자의 설정값(Options 또는 Data)을 변수로 가져옵니다.
    energy_entity = config_entry.options.get("energy_entity", config_entry.data.get("energy_entity"))
    checkday_config = int(config_entry.options.get("checkday_config", config_entry.data.get("checkday_config")))
    pressure_config = config_entry.options.get("pressure_config", config_entry.data.get("pressure_config"))
    bigfam_dc_config = int(config_entry.options.get("bigfam_dc_config", config_entry.data.get("bigfam_dc_config")))
    welfare_dc_config = int(config_entry.options.get("welfare_dc_config", config_entry.data.get("welfare_dc_config")))
    forecast_energy_entity = config_entry.options.get("forecast_energy_entity", config_entry.data.get("forecast_energy_entity"))
    prev_energy_entity = config_entry.options.get("prev_energy_entity", config_entry.data.get("prev_energy_entity"))
    prev2_energy_entity = config_entry.options.get("prev2_energy_entity", config_entry.data.get("prev2_energy_entity"))
    calibration_config = config_entry.options.get("calibration_config", config_entry.data.get("calibration_config"))
    if (forecast_energy_entity == " " or forecast_energy_entity is None):
        forecast_energy_entity = ""

    hass.data[DOMAIN]["listener"] = []

    new_devices = [] # Home Assistant에 추가될 센서 엔티티 목록

    # SENSOR_TYPES에 정의된 각 센서에 대해 객체를 생성합니다.
    for sensor_type in SENSOR_TYPES:
        # 전월/전전월 요금 센서는 해당 엔티티가 설정된 경우에만 생성합니다.
        if sensor_type == "kwhto_won_prev":
            if not _is_valid_entity_id(prev_energy_entity):
                continue
            else:
                energy_entity = prev_energy_entity
        elif sensor_type == "kwhto_won_prev2":
            if not _is_valid_entity_id(prev2_energy_entity):
                continue
            else:
                energy_entity = prev2_energy_entity
        # 보정 사용량 센서는 보정계수가 0이 아닌 경우에만 생성합니다.
        elif sensor_type == "kwhto_kwh":
            if calibration_config == 0:
                continue
        
        # 센서 객체를 생성하여 목록에 추가합니다.
        new_devices.append(
            ExtendSensor(
                hass,
                device,
                energy_entity,
                checkday_config,
                pressure_config,
                bigfam_dc_config,
                welfare_dc_config,
                forecast_energy_entity,
                calibration_config,
                sensor_type,
                device.device_id + sensor_type # Unique ID
            )
        )
        
    # 생성된 센서가 있다면 Home Assistant에 한 번에 추가합니다.
    if new_devices:
        async_add_devices(new_devices)

class SensorBase(Entity):
    """이 통합 구성요소의 모든 센서에 대한 기본 클래스입니다."""

    should_poll = False # 상태를 주기적으로 가져오지 않고, 이벤트 기반으로 업데이트합니다.
    
    def __init__(self, device):
        """센서를 초기화합니다."""
        self._device = device

    @property
    def device_info(self):
        """센서를 부모 디바이스와 연결하기 위한 정보를 반환합니다."""
        return {
            "identifiers": {(DOMAIN, self._device.device_id)},
            "name": self._device.device_id,
            "sw_version": self._device.firmware_version,
            "model": self._device.model,
            "manufacturer": self._device.manufacturer
        }

    @property
    def available(self) -> bool:
        """엔티티가 사용 가능한 상태인지 여부를 반환합니다."""
        return True
        
    async def async_added_to_hass(self):
        """엔티티가 Home Assistant에 추가될 때 실행됩니다."""
        # 디바이스의 상태 변경 콜백을 등록합니다.
        self._device.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """엔티티가 Home Assistant에서 제거되기 전에 실행됩니다."""
        # 등록했던 콜백을 제거합니다.
        self._device.remove_callback(self.async_write_ha_state)

class Device:
    """Home Assistant UI에 표시될 가상의 부모 디바이스 클래스입니다."""

    def __init__(self, name):
        """가상 디바이스를 초기화합니다."""
        self._id = name
        self.name = name
        self._callbacks = set()
        self._loop = asyncio.get_event_loop()
        
        # 디바이스의 고정된 정보
        self.firmware_version = VERSION
        self.model = MODEL
        self.manufacturer = MANUFACTURER

    @property
    def device_id(self):
        """디바이스의 ID를 반환합니다."""
        return self._id

    def register_callback(self, callback):
        """상태 변경 시 호출될 콜백 함수를 등록합니다."""
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        """등록된 콜백 함수를 제거합니다."""
        self._callbacks.discard(callback)

    async def publish_updates(self):
        """등록된 모든 콜백 함수를 실행하여 상태 업데이트를 알립니다."""
        for callback in self._callbacks:
            callback()

class ExtendSensor(SensorBase):
    """전기 요금 계산을 수행하고 상태를 표시하는 메인 센서 클래스입니다."""

    def __init__(self, hass, device,
                        energy_entity,
                        checkday_config,
                        pressure_config,
                        bigfam_dc_config,
                        welfare_dc_config,
                        forecast_energy_entity,
                        calibration_config,
                        sensor_type,
                        unique_id):
        """센서의 모든 속성을 초기화하고 리스너를 설정합니다."""
        super().__init__(device)

        self.hass = hass
        # Home Assistant에서 사용할 entity_id를 생성합니다. (예: sensor.my_device_kwhto_won)
        self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, "{}_{}".format(device.device_id, sensor_type), hass=hass)
        self._name = "{} {}".format(device.device_id, SENSOR_TYPES[sensor_type][0])
        self._state = None
        self._sensor_type = sensor_type
        self._forecast_energy_entity = forecast_energy_entity if _is_valid_entity_id(forecast_energy_entity) else None
        self._calibration = calibration_config
        self._unique_id = unique_id
        self._device = device
        self._entity_picture = None
        self._extra_state_attributes = {} # 상세 정보를 표시할 속성
        self._device_class = SENSOR_TYPES[sensor_type][1]
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][2]
        self._icon = SENSOR_TYPES[sensor_type][3]
        if SENSOR_TYPES[sensor_type][4]:
            self._extra_state_attributes['state_class'] = SENSOR_TYPES[sensor_type][4]
        self._prev_energy = 0
        if self._sensor_type == "kwhto_forecast":
            self._extra_state_attributes['last_reset'] = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        
        # 디바운싱(Debouncing): 잦은 업데이트를 방지하기 위한 취소 핸들러
        self._debounce_cancel_handle = None

        self._energy_entity = energy_entity # 원본 에너지 사용량 센서 엔티티
        self._energy = None # 현재 사용량 (kwh)
        self._energy_row = None # 보정 전 원본 사용량 (kwh)

        # 전기 요금 계산 API 클래스를 인스턴스화합니다.
        self.KWH2WON = K2WAPI(
            pressure=pressure_config,
            checkDay=checkday_config,
            today=datetime.datetime.now(),
            bigfamDcCfg=bigfam_dc_config,
            welfareDcCfg=welfare_dc_config,
            )

        # 원본 에너지 센서의 상태 변경을 감지하는 리스너를 등록합니다.
        self._energy = self.setStateListener(hass, self._energy_entity, self.energy_state_listener)
        self._energy_row = self._energy

        # 예상 사용량 센서가 별도로 지정된 경우, 해당 센서의 리스너도 등록합니다.
        if self._forecast_energy_entity:
            self.setStateListener(hass, self._forecast_energy_entity, self.forecast_energy_state_listener)

        # 초기 상태를 한 번 업데이트합니다.
        self.update()

    def setStateListener(self, hass, entity, listener):
        """지정된 엔티티에 대한 상태 변경 리스너를 등록하고 초기값을 반환합니다."""
        hass.data[DOMAIN]["listener"].append(async_track_state_change_event(
                self.hass, entity, listener))
            
        entity_state = self.hass.states.get(entity)
        if _is_valid_state(entity_state):
            return float(entity_state.state)

    @callback
    async def _async_deferred_update(self, *args):
        """디바운싱 지연 시간 후에 실제 업데이트를 트리거하는 콜백 함수입니다."""
        self._debounce_cancel_handle = None # 핸들러 초기화
        if self.enabled:
            # Home Assistant에 상태 업데이트를 요청합니다.
            # True 인자는 강제 업데이트를 의미합니다.
            await self.async_update_ha_state(True)

    @callback 
    def energy_state_listener(self, event: Event) -> None:
        """원본 에너지 센서의 상태 변경을 처리하는 리스너입니다."""
        new_state = event.data["new_state"]

        if _is_valid_state(new_state):
            new_energy = util.convert(new_state.state, float)
            if self._energy != new_energy: # 값이 실제로 변경되었을 때만 처리
                _LOGGER.debug(f"에너지 센서 상태 변경: {new_state.state}")
                self._energy = new_energy
                self._energy_row = self._energy
                
                # 디바운싱 로직: 즉시 업데이트하지 않고, 1초 뒤로 업데이트를 예약합니다.
                if self.enabled:
                    # 이전에 예약된 업데이트가 있다면 취소합니다.
                    if self._debounce_cancel_handle:
                        self._debounce_cancel_handle()
                    
                    # 1초 뒤에 _async_deferred_update 함수를 실행하도록 예약합니다.
                    self._debounce_cancel_handle = async_call_later(
                        self.hass,
                        1,  # 1초 지연
                        self._async_deferred_update
                    )

    @callback
    def forecast_energy_state_listener(self, event: Event) -> None:
        """(선택적) 예상 사용량 센서의 상태 변경을 처리하는 리스너입니다."""
        new_state = event.data["new_state"]

        if new_state is None or new_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            _LOGGER.warning(f"예상 사용량 센서 {event.data['entity_id']}가 유효하지 않습니다.")
        else:
            _LOGGER.debug(f"예상 사용량 센서 상태 변경: {new_state.state}")

        # 이 리스너도 동일하게 디바운싱 로직을 적용합니다.
        if self.enabled:
            if self._debounce_cancel_handle:
                self._debounce_cancel_handle()
            
            self._debounce_cancel_handle = async_call_later(
                self.hass,
                1, # 1초 지연
                self._async_deferred_update
            )

    @property
    def unique_id(self) -> str:
        """센서의 고유 ID를 반환합니다."""
        if self._unique_id is not None:
            return self._unique_id + self._sensor_type
            
    # --- 이하 Home Assistant 엔티티의 표준 속성들 ---
    @property
    def name(self):
        """센서의 이름을 반환합니다."""
        return self._name

    @property
    def state(self):
        """센서의 현재 상태(값)를 반환합니다."""
        if self._state == "unknown":
            return STATE_UNKNOWN
        return self._state

    @property
    def extra_state_attributes(self):
        """센서의 상세 속성(attributes)을 반환합니다."""
        return self._extra_state_attributes

    @property
    def icon(self):
        """센서의 아이콘을 반환합니다."""
        return self._icon

    @property
    def device_class(self) -> Optional[str]:
        """센서의 디바이스 클래스를 반환합니다."""
        return self._device_class

    @property
    def entity_picture(self):
        """센서의 프로필 사진을 반환합니다."""
        return self._entity_picture

    @property
    def unit_of_measurement(self):
        """센서의 측정 단위를 반환합니다."""
        return self._unit_of_measurement

    @property
    def should_poll(self):
        """폴링(주기적 상태 조회)이 필요 없음을 명시합니다."""
        return False

    # --- [수정 시작] ---
    # 예상 사용량(kWh)을 가져오는 로직을 별도의 헬퍼 메소드로 분리합니다.
    def _get_forecast_kwh(self) -> float | None:
        """
        설정에 따라 예상 사용량(kWh) 값을 가져옵니다.
        별도 센서가 지정된 경우 해당 센서의 상태를, 그렇지 않은 경우 API로 직접 계산합니다.
        유효하지 않은 경우 None을 반환합니다.
        """
        # 1. 별도의 예상 사용량 센서가 지정된 경우
        if self._forecast_energy_entity:
            state = self.hass.states.get(self._forecast_energy_entity)
            if _is_valid_state(state):
                return float(state.state)
            
            _LOGGER.warning(f"예상 사용량 센서 {self._forecast_energy_entity}의 상태가 유효하지 않아 계산할 수 없습니다.")
            return None # 상태가 유효하지 않으면 None 반환
        
        # 2. 별도 센서가 없는 경우, 현재 사용량을 기반으로 API를 통해 직접 계산
        else:
            if self._energy is None:
                return None
            forecast_info = self.KWH2WON.energy_forecast(self._energy, datetime.datetime.now())
            return forecast_info['forecast']
    # --- [수정 끝] ---

    def update(self):
        """센서의 타입에 따라 상태와 속성을 계산하고 업데이트하는 핵심 메소드입니다."""
        _LOGGER.debug(f"업데이트 시작: {self._sensor_type}, 현재 사용량: {self._energy}")
        if self._energy is not None:
            # 1. 보정계수가 설정된 경우, 사용량에 적용합니다.
            if self._calibration > 0:
                self._energy = round(self._energy_row * self._calibration, 1)

            # 2. 센서 타입별로 분기하여 상태를 계산합니다.
            if self._sensor_type == "kwhto_kwh": # 보정된 현재 사용량 센서
                self._state = self._energy
                self._extra_state_attributes['측정사용량'] = self._energy_row
                self._extra_state_attributes['보정계수'] = self._calibration
                if self._energy < self._prev_energy: # 사용량이 리셋된 경우
                    self._extra_state_attributes['last_reset'] = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
            
            # --- [수정 시작] ---
            # 중복 로직을 제거하고 새로 만든 헬퍼 메소드를 사용하도록 수정합니다.
            elif self._sensor_type == "kwhto_forecast": # 예상 전기 사용량 센서
                forecast_kwh = self._get_forecast_kwh()
                if forecast_kwh is None:
                    self._state = STATE_UNKNOWN
                    return
                
                self._state = forecast_kwh
                # 상세 속성 표시를 위해 forecast 정보는 항상 계산합니다.
                forecast = self.KWH2WON.energy_forecast(self._energy, datetime.datetime.now())
                self._extra_state_attributes['사용량'] = self._energy
                self._extra_state_attributes['검침시작일'] = f"{forecast['checkMonth']}월 {forecast['checkDay']}일"
                self._extra_state_attributes['사용일수'] = forecast['useDays']
                self._extra_state_attributes['남은일수'] = forecast['monthDays'] - forecast['useDays']
                if self._energy < self._prev_energy:
                    self._extra_state_attributes['last_reset'] = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
            
            else: # 요금(won)을 계산하는 모든 센서들
                ret = None
                if self._sensor_type == "kwhto_won": # 현재 사용 요금
                    ret = self.KWH2WON.kwh2won(self._energy, datetime.datetime.now())
                
                elif self._sensor_type == "kwhto_won_prev": # 전월 사용 요금
                    prev_day = self.KWH2WON.prev_checkday(datetime.datetime.now())
                    ret = self.KWH2WON.kwh2won(self._energy, prev_day)
                
                elif self._sensor_type == "kwhto_won_prev2": # 전전월 사용 요금
                    prev2_day = self.KWH2WON.prev2_checkday(datetime.datetime.now())
                    ret = self.KWH2WON.kwh2won(self._energy, prev2_day)
                
                elif self._sensor_type == "kwhto_forecast_won": # 예상 전기 사용 요금
                    forecast_kwh = self._get_forecast_kwh()
                    if forecast_kwh is None:
                        self._state = STATE_UNKNOWN
                        return

                    ret = self.KWH2WON.kwh2won(forecast_kwh, datetime.datetime.now())
                    self._extra_state_attributes['예상사용량'] = forecast_kwh
                # --- [수정 끝] ---
                
                # 계산 결과를 상태와 상세 속성에 반영합니다.
                self._state = ret['total']
                self._extra_state_attributes['사용량'] = self._energy
                self._extra_state_attributes['검침시작일'] = f"{ret['checkMonth']}월 {ret['checkDay']}일"
                self._extra_state_attributes['사용일수'] = ret['useDays']
                self._extra_state_attributes['남은일수'] = ret['monthDays'] - ret['useDays']
                self._extra_state_attributes['사용용도'] = PRESSURE_OPTION[ret['pressure']]
                self._extra_state_attributes['대가족_할인'] = BIGFAM_DC_OPTION[ret['bigfamDcCfg']]
                self._extra_state_attributes['복지_할인'] = WELFARE_DC_OPTION[ret['welfareDcCfg']]
                
                seasonName = {'etc':'기타','summer':'하계', 'winter':'동계'}
                season1 = None
                if ret['mm1']['useDays'] > 0:
                    season1 = seasonName[ret['mm1']['season']]
                    self._extra_state_attributes[f'누진단계_{season1}'] = ret['mm1']['kwhStep']
                if ret['mm2']['useDays'] > 0:
                    season2 = seasonName[ret['mm2']['season']]
                    if season1 == season2: season2 += '2'
                    self._extra_state_attributes[f'누진단계_{season2}'] = ret['mm2']['kwhStep']
                    
                self._extra_state_attributes['기본요금'] = ret['basicWon']
                self._extra_state_attributes['전력량요금'] = ret['kwhWon']
                self._extra_state_attributes['기후환경요금'] = ret['climateWon']
                self._extra_state_attributes['연료비조정액'] = ret['fuelWon']
                if self._energy <= 200:
                    self._extra_state_attributes['200kWh이하감액'] = ret['elecBasic200Dc'] * -1
                if ret['bigfamDcCfg'] > 0:
                    self._extra_state_attributes['대가족생명할인'] = ret['bigfamDc'] * -1
                if ret['welfareDcCfg'] > 0:
                    self._extra_state_attributes['복지요금할인'] = ret['welfareDc'] * -1
                if (ret['bigfamDcCfg'] > 0 or ret['welfareDcCfg'] > 0):
                    self._extra_state_attributes['요금동결할인'] = ret['weakDc'] * -1
                self._extra_state_attributes['전기요금계'] = ret['elecSumWon']
                self._extra_state_attributes['부가가치세'] = ret['vat']
                self._extra_state_attributes['전력산업기반기금'] = ret['baseFund']

            # 다음 리셋 감지를 위해 현재 사용량을 저장합니다.
            self._prev_energy = self._energy

    async def async_update(self):
        """Home Assistant가 상태 업데이트를 요청할 때 호출되는 비동기 메소드입니다."""
        self.update()


def _is_valid_state(state) -> bool:
    """HA 상태 객체가 유효한 숫자 값을 가지고 있는지 확인하는 헬퍼 함수입니다."""
    return (state and state.state is not None and 
            state.state != STATE_UNKNOWN and 
            state.state != STATE_UNAVAILABLE and 
            not math.isnan(float(state.state)))

def _is_valid_entity_id(entity_id) -> bool:
    """문자열이 유효한 Home Assistant 엔티티 ID 형식인지 확인하는 헬퍼 함수입니다."""
    if not entity_id:
        return False
    # 정규표현식을 사용하여 'domain.object_id' 형식을 검사합니다.
    return bool(re.match(r"^[a-z_]+\.[a-z0-9_]+$", str(entity_id)))