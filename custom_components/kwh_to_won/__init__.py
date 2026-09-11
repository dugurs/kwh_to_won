"""kWh to Won integration."""
import asyncio
import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN
from .services import async_setup_services, async_update_rates

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the kWh to Won component."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN in config:
        for entry in config[DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={CONF_SOURCE: config_entries.SOURCE_IMPORT}, data=entry
                )
            )

    # 서비스 등록
    await async_setup_services(hass, config)

    # 일 1회 (매일 새벽 04:00) rates.json 원격 최신화 확인 스케줄 등록
    async def _async_daily_update_rates(*_):
        _LOGGER.debug("정기 rates.json 원격 최신화 확인을 실행합니다.")
        await async_update_rates(hass, silent=True)

    async_track_time_change(hass, _async_daily_update_rates, hour=4, minute=0, second=0)

    # HA 시작 직후 (30초 뒤) 1회 백그라운드 확인
    async def _async_startup_check():
        await asyncio.sleep(30)
        await async_update_rates(hass, silent=True)

    hass.async_create_task(_async_startup_check())

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the component."""
    data = hass.data.setdefault(DOMAIN, {})

    entry_data = {"entities": []}
    data[entry.entry_id] = entry_data

    # 옵션 업데이트 시 자동 리로드 리스너 등록 (언로드 시 자동 해제)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_update_options(hass, entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok

