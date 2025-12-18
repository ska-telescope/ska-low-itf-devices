import os
from time import sleep

import pytest
from dotenv import load_dotenv
from tango import DevState
from tango.test_context import DeviceTestContext

from mta_chiller_device.mta_chiller_device import MTAChiller
from mta_chiller_device.device_manager import MTAChillerManager
from mta_chiller_device.utils import generate_alarms_list

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

        assert proxy.chiller_state, (
            "You must select the chiller that is currently on for this test"
        )

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


def test_generate_alarms_list():
    """Tests the function that determines what alarms should be reported for a device"""
    print("test_generate_alarms_list")

    dev_name = "MTA Chiller 2"
    attr_details = {
        "ChillAntifrzAlrCir1": {
            "name": "chiller_antifreeze_alarm",
            "is_alarm": True,
        },
        "Cmp1Overload": {
            "name": "compressor_overload_alarm",
            "is_alarm": True,
        },
        "CondFanOvLdCir1": {
            "name": "condenser_fan_overload_alarm",
            "is_alarm": True,
        },
        "Evap1PumpOverload": {
            "name": "pump_overload_alarm",
            "is_alarm": True,
        },
    }

    # Test 1: No alarms raised from the alarms endpoint for chiller 2
    # Expected outcome: All alarms are False
    test_alarms = [
        {"device_name": "MTA Chiller 1", "alarm_code": "ChillAntifrzAlrCir1"},
        {"device_name": "MTA Chiller 1", "alarm_code": "Cmp1Overload"},
    ]
    results = generate_alarms_list(test_alarms, False, attr_details, dev_name)
    assert results == {
        "chiller_antifreeze_alarm": False,
        "compressor_overload_alarm": False,
        "condenser_fan_overload_alarm": False,
        "pump_overload_alarm": False,
    }

    # Test 2: One alarm raised from the alarms endpoint for chiller 2
    # Expected outcome: One alarm is true, the rest are false
    test_alarms = [
        {"device_name": "MTA Chiller 1", "alarm_code": "ChillAntifrzAlrCir1"},
        {"device_name": "MTA Chiller 1", "alarm_code": "Cmp1Overload"},
        {"device_name": "MTA Chiller 2", "alarm_code": "ChillAntifrzAlrCir1"},
    ]
    results = generate_alarms_list(test_alarms, False, attr_details, dev_name)
    assert results == {
        "chiller_antifreeze_alarm": True,
        "compressor_overload_alarm": False,
        "condenser_fan_overload_alarm": False,
        "pump_overload_alarm": False,
    }

    # Test 3: Two alarms raised from the alarms endpoint for chiller 2
    # Expected outcome: Two alarms are true, the rest are false
    test_alarms = [
        {"device_name": "MTA Chiller 1", "alarm_code": "ChillAntifrzAlrCir1"},
        {"device_name": "MTA Chiller 1", "alarm_code": "Cmp1Overload"},
        {"device_name": "MTA Chiller 2", "alarm_code": "ChillAntifrzAlrCir1"},
        {"device_name": "MTA Chiller 2", "alarm_code": "Evap1PumpOverload"},
    ]
    results = generate_alarms_list(test_alarms, False, attr_details, dev_name)
    assert results == {
        "chiller_antifreeze_alarm": True,
        "compressor_overload_alarm": False,
        "condenser_fan_overload_alarm": False,
        "pump_overload_alarm": True,
    }

    # Test 4: No alarms are raised from a socket message for chiller 2
    # Expected outcome: The results dict is empty - I.e. no changes
    test_alarms = [
        {"device_name": "MTA Chiller 1", "alarm_code": "ChillAntifrzAlrCir1"},
        {"device_name": "MTA Chiller 1", "alarm_code": "Cmp1Overload"},
    ]
    results = generate_alarms_list(test_alarms, True, attr_details, dev_name)
    assert results == {}

    # Test 5: One alarm is raised from a socket message for chiller 2
    # Expected outcome: One alarm is true
    test_alarms = [
        {"device_name": "MTA Chiller 1", "alarm_code": "ChillAntifrzAlrCir1"},
        {"device_name": "MTA Chiller 1", "alarm_code": "Cmp1Overload"},
        {"device_name": "MTA Chiller 2", "alarm_code": "Cmp1Overload"},
    ]
    results = generate_alarms_list(test_alarms, True, attr_details, dev_name)
    assert results == {
        "compressor_overload_alarm": True,
    }

    # Test 6: Two alarms are raised from a socket message for chiller 2
    # Expected outcome: Two alarms are true
    test_alarms = [
        {"device_name": "MTA Chiller 1", "alarm_code": "ChillAntifrzAlrCir1"},
        {"device_name": "MTA Chiller 1", "alarm_code": "Cmp1Overload"},
        {"device_name": "MTA Chiller 2", "alarm_code": "Cmp1Overload"},
        {"device_name": "MTA Chiller 2", "alarm_code": "ChillAntifrzAlrCir1"},
    ]
    results = generate_alarms_list(test_alarms, True, attr_details, dev_name)
    assert results == {
        "compressor_overload_alarm": True,
        "chiller_antifreeze_alarm": True,
    }

    print("PASSED")


if __name__ == "__main__":
    # test_init()
    # test_attributes()
    # test_reconnect()
    test_generate_alarms_list()
    # IMPORTANT: Only uncomment below if you have access to the XWeb Evo online dashboard
    # test_powercycle()
