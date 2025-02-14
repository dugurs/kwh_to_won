"""The Detailed Hello World Push integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant


from .const import DOMAIN

from homeassistant.helpers.device_registry import (
    async_get,
    async_entries_for_config_entry
)

from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Hello World component."""
    if DOMAIN in config:
        for entry in config[DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={CONF_SOURCE: SOURCE_IMPORT}, data=entry
                )
            )

    # 서비스 등록
    await async_setup_services(hass, config)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the component."""
    data = hass.data.setdefault(DOMAIN, {})

    undo_listener = entry.add_update_listener(async_update_options)
    data[entry.entry_id] = {"undo_update_listener": undo_listener}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True
    

async def async_update_options(hass, entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    
    # for listener in hass.data[DOMAIN]["listener"]:
    #     listener()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

