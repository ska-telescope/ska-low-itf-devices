import logging
import time
from typing import Any

import pytest
from ska_control_model import CommunicationStatus

from ska_low_itf_devices.attribute_polling_component_manager import AttrInfo
from ska_proxr_device.proxr_component_manager import ProXRComponentManager


@pytest.fixture
def component_manager(endpoint):
    def comm_state_changed(comm_state: CommunicationStatus) -> None:
        pass

    def component_state_changed(state_updates: dict[str, Any]) -> None:
        pass

    host, port = endpoint

    return ProXRComponentManager(
        host=host,
        port=port,
        logger=logging.getLogger(),
        communication_state_callback=comm_state_changed,
        component_state_callback=component_state_changed,
        attributes=[
            AttrInfo(
                attr_args=dict(
                    name="fast",
                    dtype=int,
                ),
                polling_period=0.5,
            ),
            AttrInfo(
                attr_args=dict(
                    name="slow",
                    dtype=int,
                ),
                polling_period=1.0,
            ),
        ],
        poll_rate=2.0,
    )


def test_component_manager_polling_periods(component_manager):
    mgr = component_manager
    assert all(t == float("-inf") for t in mgr._last_polled.values())

    def time_travel(d: float) -> None:
        mgr._last_polled.update((k, v - d) for k, v in mgr._last_polled.items())

    attrs_to_poll = set(mgr.get_request().reads)
    assert attrs_to_poll == {"slow", "fast"}

    now = time.time()
    mgr._last_polled.update({"slow": now, "fast": now})

    time_travel(0.25)
    assert not mgr.get_request().reads

    time_travel(0.5)
    to_poll = set(mgr.get_request().reads)
    assert to_poll == {"fast"}

    time_travel(0.5)
    to_poll = set(mgr.get_request().reads)
    assert to_poll == {"slow", "fast"}

    mgr._last_polled["fast"] = time.time()
    to_poll = set(mgr.get_request().reads)
    assert to_poll == {"slow"}
