import datetime
import logging
from .kwh2won_api import kwh2won_api
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CALCULATE_SCHEMA = vol.Schema(
    {
        vol.Required("kwh"): vol.Coerce(float),
        vol.Required("pressure"): cv.string,
        vol.Required("checkDay", default=0): vol.Coerce(int),
        vol.Required("today"): cv.string,
        vol.Optional("bigfamDcCfg", default=0): vol.Coerce(int),
        vol.Optional("welfareDcCfg", default=0): vol.Coerce(int),
    }
)
async def async_setup_services(hass: HomeAssistant, config: ConfigType) -> None:
    async def calculate(call: ServiceCall) -> ServiceResponse:

        kwh = call.data.get('kwh')
        pressure = call.data.get('pressure')
        checkDay = call.data.get('checkDay')
        today_str = call.data.get('today')
        bigfamDcCfg = call.data.get('bigfamDcCfg')
        welfareDcCfg = call.data.get('welfareDcCfg')
        _LOGGER.info(f"전기요금 계산 : kwh:{kwh} pressure:{pressure} checkDay:{checkDay} today:{today_str} bigfamDcCfg:{bigfamDcCfg} welfareDcCfg:{welfareDcCfg}")

        if kwh is not None:
            # today를 datetime 객체로 변환
            today = datetime.datetime.strptime(today_str, "%Y-%m-%d")

            # kwh2won_api 인스턴스 생성
            kwh2won_api_instance = kwh2won_api(
                pressure=pressure,
                checkDay=checkDay,
                today=today,
                bigfamDcCfg=bigfamDcCfg,
                welfareDcCfg=welfareDcCfg
            )
            result = kwh2won_api_instance.kwh2won(kwh)
            _LOGGER.info(f"Calculated electricity bill for {kwh} kWh: {result}")
            

        else:
            _LOGGER.error("No kWh value provided for electricity bill calculation")
            result = {}

        return result

    hass.services.async_register(
        DOMAIN,
        'calculate',
        calculate,
        schema=CALCULATE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )