"""This module contains a PyTango device for monitoring and controlling the MTA Chillers."""

import os
from time import time

from tango import AttrQuality, DevState
from tango.server import Device, attribute, command, device_property, run

from mta_chiller_device.custom_types import ClientConfig
from mta_chiller_device.device_manager import MTAChillerManager


class MTAChiller(Device):
    """A PyTango device for the MTA Chillers."""

    # Define the device properties
    model = device_property(dtype=str, default_value="XIC208CX")
    host = device_property(dtype=str)
    device_name = device_property(
        dtype=str
    )  # The chiller name used in the XWeb Evo system
    alarm_polling_period = device_property(dtype=int, default_value=60)

    def __init__(self, device_class, device_name):
        super().__init__(device_class, device_name)

        # Create variables for tracking the device state
        self._communication_state: str = (
            "NOT_ESTABLISHED"  # One of 'NOT_ESTABLISHED', 'ESTABLISHED', 'DISABLED'
        )
        self._component_power: str = "OFF"  # One of 'OFF', 'ON'
        self._fault: bool = False

    def init_device(self):
        """Initialise device."""
        super().init_device()
        self.set_state(DevState.UNKNOWN)

        # Configure the attributes to be manually updated
        self.set_change_event("tank_outlet_temp", True)
        self.set_change_event("evaporator_outlet_temp", True)
        self.set_change_event("set_point", True)
        self.set_change_event("chiller_state", True)
        self.set_change_event("compressor_state", True)
        self.set_change_event("water_pump_state", True)
        self.set_change_event("chiller_antifreeze_alarm", True)
        self.set_change_event("compressor_overload_alarm", True)
        self.set_change_event("condenser_fan_overload_alarm", True)
        self.set_change_event("pump_overload_alarm", True)
        self.set_change_event("evaporator_flow_switch_alarm", True)
        self.set_change_event("general_phase_monitor_alarm", True)
        self.set_change_event("high_pressure_switch_alarm", True)
        self.set_change_event("low_pressure_switch_alarm", True)
        self.set_change_event("chiller_disconnected_alarm", True)
        self.set_change_event("probe_1_alarm", True)
        self.set_change_event("probe_2_alarm", True)

        # Create an instance of the chiller device manager
        client_config: ClientConfig = {
            "ip_address": self.host,
            "username": os.getenv("XWEB_USERNAME"),
            "hashed_password": os.getenv("XWEB_HASHED_PASSWORD"),
        }
        self._chiller_manager = MTAChillerManager(
            client_config,
            self.device_name,
            self.update_communication_state,
            self.update_component_state,
            self.update_attribute,
            alarm_polling_period=self.alarm_polling_period,
        )

        self._chiller_manager.start_communicating()

    def delete_device(self):
        """Stop communicating before deleting Tango device."""
        self._chiller_manager.stop_communicating()
        super().delete_device()

    #### Device attributes ####

    @attribute(dtype=float, unit="°C")
    def tank_outlet_temp(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("tank_outlet_temp")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        return attr

    @attribute(dtype=float, unit="°C")
    def evaporator_outlet_temp(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("evaporator_outlet_temp")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        return attr

    @attribute(dtype=float, unit="°C")
    def set_point(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("set_point")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        return attr

    @attribute(dtype=bool)
    def chiller_state(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("chiller_state")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        return attr

    @chiller_state.write
    def chiller_state(self, state):
        """Write method for attribute."""
        if state:
            self._chiller_manager.chiller_on()
        else:
            self._chiller_manager.chiller_off()

    @attribute(dtype=bool)
    def compressor_state(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("compressor_state")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        return attr

    @attribute(dtype=bool)
    def water_pump_state(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("water_pump_state")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        return attr

    #### Device Alarm Attributes ####

    @attribute(dtype=bool)
    def chiller_antifreeze_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("chiller_antifreeze_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def compressor_overload_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("compressor_overload_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def condenser_fan_overload_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("condenser_fan_overload_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def pump_overload_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("pump_overload_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def evaporator_flow_switch_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("evaporator_flow_switch_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def general_phase_monitor_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("general_phase_monitor_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def high_pressure_switch_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("high_pressure_switch_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def low_pressure_switch_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("low_pressure_switch_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def chiller_disconnected_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("chiller_disconnected_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def probe_1_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("probe_1_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    @attribute(dtype=bool)
    def probe_2_alarm(self):
        """Read method for attribute."""
        attr = self._chiller_manager.get_attribute_value("probe_2_alarm")
        if attr is None:
            return None, time(), AttrQuality.ATTR_INVALID
        elif attr is True:
            return attr, time(), AttrQuality.ATTR_ALARM
        else:
            return attr

    #### Commands ####

    @command
    def mute_alarms(self):
        """Mutes all alarms."""
        self._chiller_manager.alarm_mute()

    @command
    def reset_alarms(self):
        """Reset all alarms."""
        self._chiller_manager.alarm_reset()

    #### Callback functions ####

    def update_communication_state(self, state: str):
        """Update the communication state of the device."""
        self._communication_state = state

        self._update_state()

    def update_component_state(
        self, power: str | None = None, fault: bool | None = None
    ):
        """Update the component state of the device."""
        if power is not None:
            self._component_power = power
        if fault is not None:
            self._fault = fault

        self._update_state()

    def update_attribute(
        self, attr_name: str, value: int | float | str, in_alarm=False
    ):
        """Update a particular attribute."""
        if in_alarm:
            self.push_change_event(attr_name, value, time(), AttrQuality.ATTR_ALARM)
        else:
            self.push_change_event(attr_name, value, time(), AttrQuality.ATTR_VALID)

    #### Helper functions ####

    def _update_state(self):
        """Implement the operational state matrix."""

        if self._communication_state == "DISABLED":
            self.set_state(DevState.DISABLE)
        elif self._communication_state == "NOT_ESTABLISHED":
            self.set_state(DevState.UNKNOWN)
        elif self._communication_state == "ESTABLISHED":
            if self._fault:
                if self._component_power == "OFF":
                    self.set_state(DevState.OFF)
                else:
                    self.set_state(DevState.FAULT)
            else:
                if self._component_power == "ON":
                    self.set_state(DevState.ON)
                else:
                    self.set_state(DevState.OFF)
        else:
            self.set_state(DevState.UNKNOWN)

        print(self.dev_state())


def main() -> int:  # pragma: no cover
    """
    Entry point for module.

    :param args: positional arguments
    :param kwargs: named arguments

    :return: exit code
    """
    return run([MTAChiller])


if __name__ == "__main__":
    main()
