from typing import Any

from ska_control_model import CommunicationStatus, PowerState
from ska_tango_base import SKABaseDevice
from tango import AttReqType, Attribute, AttrQuality, WAttribute
from tango.server import attribute, device_property

from .definitions import load_device_definition, parse_device_definition
from .snmp_component_manager import SNMPComponentManager
from .types import SNMPAttrInfo


class SNMPDevice(SKABaseDevice[SNMPComponentManager]):
    DeviceDefinition = device_property(dtype=str)
    Model = device_property(dtype=str)
    Host = device_property(dtype=str)
    Port = device_property(dtype=int, default_value=161)
    Community = device_property(dtype=str, default_value="private")
    UpdateRate = device_property(dtype=float, default_value=2.0)
    MaxObjectsPerSNMPCmd = device_property(dtype=int, default_value=24)

    def create_component_manager(self) -> SNMPComponentManager:
        """Create and return a component manager. Called during init_device()."""
        # This goes here because you don't have access to properties
        # until tango.server.BaseDevice.init_device() has been called
        dynamic_attrs = parse_device_definition(
            load_device_definition(self.DeviceDefinition)
        )

        # pylint: disable-next=attribute-defined-outside-init
        self._dynamic_attrs: dict[str, SNMPAttrInfo] = {
            attr.name: attr for attr in dynamic_attrs
        }

        return SNMPComponentManager(
            host=self.Host,
            port=self.Port,
            community=self.Community,
            max_objects_per_pdu=self.MaxObjectsPerSNMPCmd,
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
            snmp_attributes=dynamic_attrs,
            poll_rate=self.UpdateRate,
        )

    def initialize_dynamic_attributes(self) -> None:
        """Do what the name says. Called by Tango during init_device()."""
        for name, attr_info in self._dynamic_attrs.items():
            # partial(self._dynamic_is_allowed, name) doesn't work here
            # because Tango is too clever with the callback
            def _dynamic_is_allowed(req: AttReqType, name: str = name) -> bool:
                return self._dynamic_is_allowed(name, req)

            attr = attribute(
                fget=self._dynamic_get,
                fset=self._dynamic_set,
                fisallowed=_dynamic_is_allowed,
                **attr_info.attr_args,
            )
            self.add_attribute(attr)

            # Allow clients to subscribe to changes for this property
            self.set_change_event(name, True)

    def _dynamic_is_allowed(self, attr_name: str, _: AttReqType) -> bool:
        # pylint: disable=unused-argument
        return (
            self.component_manager.communication_state
            == CommunicationStatus.ESTABLISHED
        )

    def _dynamic_get(self, attr: Attribute) -> None:
        # pylint: disable=protected-access
        val = self.component_manager._component_state[attr.get_name()]
        if val is None:
            attr.set_quality(AttrQuality.ATTR_INVALID)
        else:
            attr.set_quality(AttrQuality.ATTR_VALID)
            attr.set_value(val)

    def _dynamic_set(self, attr: WAttribute) -> None:
        value = attr.get_write_value()
        attr_name = attr.get_name()
        self.component_manager.enqueue_write(attr_name, value)

    def _component_state_changed(
        self,
        fault: bool | None = None,
        power: PowerState | None = None,
        **kwargs: dict[str, Any],
    ) -> None:
        super()._component_state_changed(fault=fault, power=power)
        for name, value in kwargs.items():
            self.push_change_event(name, value)