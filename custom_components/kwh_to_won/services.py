import datetime
import json
import logging
from pathlib import Path
import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components import persistent_notification
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    RATES_URL,
    SERVICE_CALCULATE,
    SERVICE_RELOAD_RATES,
    SERVICE_UPDATE_RATES,
)
from .kwh2won_api import kwh2won_api, reload_rates_data, validate_rates_data

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


def _refresh_all_entities(hass: HomeAssistant) -> None:
    """등록된 모든 kwh_to_won 센서의 요금표를 다시 연결하고 상태 업데이트를 트리거합니다."""
    domain_data = hass.data.get(DOMAIN, {})
    for entry_id, entry_data in domain_data.items():
        if isinstance(entry_data, dict) and "entities" in entry_data:
            for entity in entry_data["entities"]:
                if hasattr(entity, "KWH2WON") and hasattr(entity.KWH2WON, "reload_rates"):
                    entity.KWH2WON.reload_rates()
                entity.async_schedule_update_ha_state(True)


async def async_reload_rates(hass: HomeAssistant) -> bool:
    """로컬 rates.json 파일을 다시 로드하여 메모리에 반영하고 모든 센서를 갱신합니다."""
    def _reload():
        return reload_rates_data()

    success = await hass.async_add_executor_job(_reload)
    if success:
        _refresh_all_entities(hass)
        return True
    return False


async def async_update_rates(hass: HomeAssistant, silent: bool = True) -> bool:
    """GitHub에서 최신 rates.json을 안전하게 다운로드하여 검증 후 갱신합니다."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(RATES_URL, timeout=10) as resp:
            if resp.status != 200:
                _LOGGER.warning(f"GitHub에서 요금표 다운로드 실패 (HTTP {resp.status})")
                if not silent:
                    persistent_notification.async_create(
                        hass,
                        f"GitHub에서 요금표 다운로드에 실패했습니다 (HTTP {resp.status}). 기존 요금표를 유지합니다.",
                        title="전기요금 계산기 (kWh to Won)",
                        notification_id=f"{DOMAIN}_rates_update_status",
                    )
                return False
            content = await resp.text()
            new_rates = json.loads(content)
    except Exception as err:
        _LOGGER.warning(f"GitHub 요금표 조회 중 네트워크 오류: {err}")
        if not silent:
            persistent_notification.async_create(
                hass,
                f"요금표 다운로드 중 네트워크 오류가 발생했습니다: {err}\n기존 요금표를 안전하게 유지합니다.",
                title="전기요금 계산기 (kWh to Won)",
                notification_id=f"{DOMAIN}_rates_update_status",
            )
        return False

    if not validate_rates_data(new_rates):
        _LOGGER.error("다운로드된 요금표 데이터의 형식이 올바르지 않습니다.")
        if not silent:
            persistent_notification.async_create(
                hass,
                "다운로드된 요금표 형식이 올바르지 않아 적용이 취소되었습니다. 기존 요금표를 유지합니다.",
                title="전기요금 계산기 (kWh to Won)",
                notification_id=f"{DOMAIN}_rates_update_status",
            )
        return False

    # 기존 로컬 파일과 비교하여 변경 사항이 있을 때만 저장
    def _save_if_changed():
        rates_path = Path(__file__).parent / "rates.json"
        try:
            with open(rates_path, "r", encoding="utf-8") as f:
                current_rates = json.load(f)
            if json.dumps(current_rates, sort_keys=True) == json.dumps(new_rates, sort_keys=True):
                return False, True  # changed=False, success=True
        except Exception:
            pass

        temp_path = rates_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(new_rates, f, ensure_ascii=False, indent=4)
        temp_path.replace(rates_path)
        reload_rates_data()
        return True, True  # changed=True, success=True

    changed, success = await hass.async_add_executor_job(_save_if_changed)
    if not success:
        return False

    if changed:
        _LOGGER.info("한전 전기요금표(rates.json)가 최신 버전으로 갱신되었습니다.")
        _refresh_all_entities(hass)
        persistent_notification.async_create(
            hass,
            "한전 전기요금표(rates.json)가 GitHub 최신 버전으로 자동 업데이트되어 즉시 반영되었습니다.",
            title="전기요금 계산기 (kWh to Won)",
            notification_id=f"{DOMAIN}_rates_updated",
        )
    else:
        _LOGGER.debug("요금표(rates.json)가 이미 최신 상태입니다.")
        if not silent:
            persistent_notification.async_create(
                hass,
                "현재 요금표가 이미 GitHub 최신 버전과 동일합니다.",
                title="전기요금 계산기 (kWh to Won)",
                notification_id=f"{DOMAIN}_rates_update_status",
            )
    return True


async def async_setup_services(hass: HomeAssistant, config: ConfigType) -> None:
    """전기요금 계산기 서비스를 등록합니다."""
    async def calculate(call: ServiceCall) -> ServiceResponse:
        kwh = call.data.get('kwh')
        pressure = call.data.get('pressure')
        checkDay = call.data.get('checkDay')
        today_str = call.data.get('today')
        bigfamDcCfg = call.data.get('bigfamDcCfg')
        welfareDcCfg = call.data.get('welfareDcCfg')
        _LOGGER.info(f"전기요금 계산 : kwh:{kwh} pressure:{pressure} checkDay:{checkDay} today:{today_str} bigfamDcCfg:{bigfamDcCfg} welfareDcCfg:{welfareDcCfg}")

        if kwh is not None:
            today = datetime.datetime.strptime(today_str, "%Y-%m-%d")
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

    async def handle_reload_rates(call: ServiceCall) -> None:
        """로컬 rates.json 재로드 서비스 핸들러."""
        success = await async_reload_rates(hass)
        if success:
            _LOGGER.info("요금표(rates.json)를 성공적으로 다시 로드했습니다.")
        else:
            _LOGGER.error("요금표(rates.json) 다시 로드에 실패했습니다.")

    async def handle_update_rates(call: ServiceCall) -> None:
        """원격 rates.json 업데이트 서비스 핸들러."""
        await async_update_rates(hass, silent=False)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CALCULATE,
        calculate,
        schema=CALCULATE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD_RATES,
        handle_reload_rates,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_RATES,
        handle_update_rates,
    )