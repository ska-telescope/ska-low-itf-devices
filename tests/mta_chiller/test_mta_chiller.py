import os
from time import sleep

import pytest
from dotenv import load_dotenv
from tango import DevState
from tango.test_context import DeviceTestContext

from mta_chiller_device.mta_chiller_device import MTAChiller

# Load env variables
load_dotenv()
ip = os.getenv("BASE_IP")

properties = {"host": ip, "device_name": "MTA Chiller 2"}


@pytest.mark.skipif(not bool(ip), reason="Chiller IP address not defined")
def test_init():
    """Tests whether the MTA chiller device initialises correctly"""
    print("test_init")

    with DeviceTestContext(MTAChiller, properties=properties) as proxy:
        assert proxy.state() == DevState.UNKNOWN
        sleep(10)
        assert proxy.state() == DevState.ON

    print("PASSED")


def manual_test_powercycle():
    """Tests whether the powercycle functionality works correctly. Do not run this test automatically."""
    print("test_powercycle")

    with DeviceTestContext(MTAChiller, properties=properties) as proxy:
        sleep(20)

        assert (
            proxy.chiller_state
        ), "You must select the chiller that is currently on for this test"

        proxy.chiller_state = False
        sleep(10)
        assert proxy.chiller_state is False
        proxy.chiller_state = True
        sleep(10)
        assert proxy.chiller_state is True

    print("PASSED: Please check that one chiller is switched ON")


@pytest.mark.skipif(not bool(ip), reason="Chiller IP address not defined")
def test_attributes() -> None:
    """Tests whether the MTA Chiller attributes are exposed correctly through the tango device"""
    print("test_attributes")

    with DeviceTestContext(MTAChiller, properties=properties) as proxy:
        sleep(20)
        assert isinstance(proxy.chiller_state, bool)
        assert isinstance(proxy.water_pump_state, bool)
        assert isinstance(proxy.compressor_state, bool)
        assert isinstance(proxy.tank_outlet_temp, float)
        assert isinstance(proxy.evaporator_outlet_temp, float)
        assert isinstance(proxy.set_point, float)
        assert isinstance(proxy.chiller_antifreeze_alarm, bool)
        assert isinstance(proxy.compressor_overload_alarm, bool)
        assert isinstance(proxy.condenser_fan_overload_alarm, bool)
        assert isinstance(proxy.pump_overload_alarm, bool)
        assert isinstance(proxy.evaporator_flow_switch_alarm, bool)
        assert isinstance(proxy.general_phase_monitor_alarm, bool)
        assert isinstance(proxy.high_pressure_switch_alarm, bool)
        assert isinstance(proxy.low_pressure_switch_alarm, bool)
        assert isinstance(proxy.chiller_disconnected_alarm, bool)
        assert isinstance(proxy.probe_1_alarm, bool)
        assert isinstance(proxy.probe_2_alarm, bool)

        assert proxy.tank_outlet_temp > 0
        assert proxy.evaporator_outlet_temp > 0
        assert proxy.set_point > 0

        assert not proxy.chiller_antifreeze_alarm
        assert not proxy.compressor_overload_alarm
        assert not proxy.condenser_fan_overload_alarm
        assert not proxy.pump_overload_alarm
        assert not proxy.evaporator_flow_switch_alarm
        assert not proxy.general_phase_monitor_alarm
        assert not proxy.high_pressure_switch_alarm
        assert not proxy.low_pressure_switch_alarm
        assert not proxy.chiller_disconnected_alarm
        assert not proxy.probe_1_alarm
        assert not proxy.probe_2_alarm

    print("PASSED")


def manual_test_reconnect():
    """Tests that the chiller device successfully reconnects after a network interruption"""
    print("test_reconnect")

    with DeviceTestContext(MTAChiller, properties=properties) as proxy:
        assert proxy.state() == DevState.UNKNOWN
        sleep(10)
        assert proxy.state() == DevState.ON

        print("Now, disconnect your computer from the network")
        input("Done?")
        sleep(60)
        assert proxy.state() == DevState.UNKNOWN

        print("Now, reconnect your computer")
        input("Done?")
        sleep(70)
        assert proxy.state() == DevState.ON

    print("PASSED")


if __name__ == "__main__":
    # test_init()
    test_attributes()
    # test_reconnect()
    # IMPORTANT: Only uncomment below if you have access to the XWeb Evo online dashboard
    # test_powercycle()
