"""Support for custom shell commands to retrieve values."""
from __future__ import annotations

from datetime import timedelta

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    DOMAIN as BINARY_SENSOR_DOMAIN,
    PLATFORM_SCHEMA,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import (
    CONF_COMMAND,
    CONF_DEVICE_CLASS,
    CONF_NAME,
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
    CONF_UNIQUE_ID,
    CONF_VALUE_TEMPLATE,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.template import Template
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_COMMAND_TIMEOUT, DEFAULT_TIMEOUT, DOMAIN
from .sensor import CommandSensorData

DEFAULT_NAME = "Binary Command Sensor"
DEFAULT_PAYLOAD_ON = "ON"
DEFAULT_PAYLOAD_OFF = "OFF"

SCAN_INTERVAL = timedelta(seconds=60)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_COMMAND): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
        vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
        vol.Optional(CONF_COMMAND_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Command line Binary Sensor."""

    if binary_sensor_config := config:
        async_create_issue(
            hass,
            DOMAIN,
            "deprecated_yaml_binary_sensor",
            breaks_in_ha_version="2023.8.0",
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_platform_yaml",
            translation_placeholders={"platform": BINARY_SENSOR_DOMAIN},
        )
    if discovery_info:
        binary_sensor_config = discovery_info

    name: str = binary_sensor_config.get(CONF_NAME, DEFAULT_NAME)
    command: str = binary_sensor_config[CONF_COMMAND]
    payload_off: str = binary_sensor_config[CONF_PAYLOAD_OFF]
    payload_on: str = binary_sensor_config[CONF_PAYLOAD_ON]
    device_class: BinarySensorDeviceClass | None = binary_sensor_config.get(
        CONF_DEVICE_CLASS
    )
    value_template: Template | None = binary_sensor_config.get(CONF_VALUE_TEMPLATE)
    command_timeout: int = binary_sensor_config[CONF_COMMAND_TIMEOUT]
    unique_id: str | None = binary_sensor_config.get(CONF_UNIQUE_ID)
    if value_template is not None:
        value_template.hass = hass
    data = CommandSensorData(hass, command, command_timeout)

    async_add_entities(
        [
            CommandBinarySensor(
                data,
                name,
                device_class,
                payload_on,
                payload_off,
                value_template,
                unique_id,
            )
        ],
        True,
    )


class CommandBinarySensor(BinarySensorEntity):
    """Representation of a command line binary sensor."""

    def __init__(
        self,
        data: CommandSensorData,
        name: str,
        device_class: BinarySensorDeviceClass | None,
        payload_on: str,
        payload_off: str,
        value_template: Template | None,
        unique_id: str | None,
    ) -> None:
        """Initialize the Command line binary sensor."""
        self.data = data
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_is_on = None
        self._payload_on = payload_on
        self._payload_off = payload_off
        self._value_template = value_template
        self._attr_unique_id = unique_id

    async def async_update(self) -> None:
        """Get the latest data and updates the state."""
        await self.hass.async_add_executor_job(self.data.update)
        value = self.data.value

        if self._value_template is not None:
            value = self._value_template.async_render_with_possible_json_value(
                value, None
            )
        self._attr_is_on = None
        if value == self._payload_on:
            self._attr_is_on = True
        elif value == self._payload_off:
            self._attr_is_on = False
