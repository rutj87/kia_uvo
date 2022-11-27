"""Number for Hyundai / Kia Connect integration."""
from __future__ import annotations

import logging
from typing import Final

from hyundai_kia_connect_api import Vehicle, VehicleManager
from hyundai_kia_connect_api.Vehicle import EvChargeLimits

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HyundaiKiaConnectDataUpdateCoordinator
from .entity import HyundaiKiaConnectEntity

_LOGGER = logging.getLogger(__name__)

AC_CHARGING_LIMIT_KEY = "_ac_charging_limit"
DC_CHARGING_LIMIT_KEY = "_dc_charging_limit"

NUMBER_DESCRIPTIONS: Final[tuple[NumberEntityDescription, ...]] = (
    NumberEntityDescription(
        key=AC_CHARGING_LIMIT_KEY,
        name="AC Charging Limit",
        icon="mdi:ev-plug-type2",
        native_min_value=50,
        native_max_value=100,
        native_step=10,
    ),
    NumberEntityDescription(
        key=DC_CHARGING_LIMIT_KEY,
        name="DC Charging Limit",
        icon="mdi:ev-plug-ccs2",
        native_min_value=50,
        native_max_value=100,
        native_step=10,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][config_entry.unique_id]
    entities = []
    for vehicle_id in coordinator.vehicle_manager.vehicles.keys():
        vehicle: Vehicle = coordinator.vehicle_manager.vehicles[vehicle_id]
        for description in NUMBER_DESCRIPTIONS:
            if getattr(vehicle, description.key, None) is not None:
                entities.append(
                    HyundaiKiaConnectNumber(coordinator, description, vehicle)
                )

    async_add_entities(entities)
    return True


class HyundaiKiaConnectNumber(NumberEntity, HyundaiKiaConnectEntity):
    def __init__(
        self,
        coordinator: HyundaiKiaConnectDataUpdateCoordinator,
        description: NumberEntityDescription,
        vehicle: Vehicle,
    ) -> None:
        super().__init__(coordinator, vehicle)
        self._description = description
        self._key = self._description.key
        self._attr_unique_id = f"{DOMAIN}_{vehicle.id}_{self._key}"
        self._attr_icon = self._description.icon
        self._attr_name = f"{vehicle.name} {self._description.name}"
        self._attr_state_class = self._description.state_class
        self._attr_device_class = self._description.device_class

    @property
    def native_value(self) -> float | None:
        """Return the entity value to represent the entity state."""
        if self.entity_description.key == AC_CHARGING_LIMIT_KEY:
            return self.vehicle.ev_charge_limits.ac
        else:
            return self.vehicle.ev_charge_limits.dc

    async def async_set_native_value(self, value: float) -> None:
        """Set new charging limit."""
        # force refresh of state so that we can get the value for the other charging limit
        # since we have to set both limits as compound API call.
        await self.coordinator.async_force_update_all()

        if (
            self.entity_description.key == AC_CHARGING_LIMIT_KEY
            and self.vehicle.ev_charge_limits.ac == int(value)
        ):
            return
        if (
            self.entity_description.key == DC_CHARGING_LIMIT_KEY
            and self.vehicle.ev_charge_limits.dc == int(value)
        ):
            return

        # set new limits
        self._vehicle.ev_charge_limits = (
            EvChargeLimits(ac=value, dc=vehicle.ev_charge_limits.dc)
            if self.entity_description.key == AC_CHARGING_LIMIT_KEY
            else EvChargeLimits(ac=self.vehicle.ev_charge_limits.ac, dc=value)
        )
        await self.coordinator.async_set_charge_limits(
            self.vehicle.id, EvChargeLimits(ac=value, dc=current_limits.dc)
        )

        self.async_write_ha_state()
