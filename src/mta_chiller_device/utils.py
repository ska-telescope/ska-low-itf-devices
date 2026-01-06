"""This module contains util functions for transforming HTTP responses and other functions."""

import json
from urllib.parse import unquote

import pydash as _

from mta_chiller_device.custom_types import (
    Alarm,
    ClientAttribute,
    ClientCommand,
    ClientDevice,
    ControlGroup,
    Datapoint,
    AttributeDetails,
)


def transform_to_credentials(response) -> tuple[str, str]:
    """Extract the session key and command key from the HTTP response."""

    sses: str = _.get(response, "sses", None)

    # find the plgid used to authenticate command requests
    plgid_obj = (
        _.chain(response)
        .get("ucfg", {})
        .values()
        .map_("plugins")
        .map_(_.values)
        .flatten()
        .find(lambda plugin: _.get(plugin, "ptype", "") == "commandButtons")
        .value()
    )

    plgid: str = _.get(plgid_obj, "pid", None)

    return sses, plgid


def transform_to_config(response) -> tuple[list[ControlGroup], list[ClientDevice]]:
    """Extract the control groups and devices from the HTTP response."""

    # Locate the control groups
    control_groups: list[ControlGroup] = (
        _.chain(response)
        .get("setup.ctgs", {})
        .for_in(lambda value, key: value.update({"id": key}))
        .values()
        .map_(
            (
                lambda value: {
                    "name": unquote(value["term"]),
                    "devices": value["devs"],
                    "id": value["id"],
                }
            )
        )
        .value()
    )

    # Locate the devices
    devices: list[ClientDevice] = (
        _.chain(response)
        .get("devices", {})
        .map_values(
            (
                lambda device, key: {
                    "address": _.get(device, "dev.gen.addr", ""),
                    "description": unquote(_.get(device, "dev.gen.desc", "")),
                    "name": unquote(_.get(device, "dev.gen.name", "")),
                    "model": _.get(device, "dev.gen.model", ""),
                    "commands": transform_to_commands(device),
                    "attributes": transform_to_attributes(device),
                    "id": key,
                }
            )
        )
        .value()
    )

    return control_groups, devices


def transform_to_commands(device) -> list[ClientCommand]:
    """Extract all the available commands for a device from the HTTP response."""

    commands: list[ClientCommand] = (
        _.chain(device)
        .get("dev.cmds", {})
        .map_values(
            (
                lambda value, key: {
                    "name": unquote(_.get(value, "cn", "")),
                    "readable_name": _.get(device, f"lng.cmds.{key}.cds", ""),
                    "id": key,
                }
            )
        )
        .value()
    )

    return commands


def transform_to_attributes(device) -> list[ClientAttribute]:
    """Extract all the available attributes for a device from the HTTP response."""

    attributes: list[ClientAttribute] = (
        _.chain(device)
        .get("dev.vrs", {})
        .map_values(
            (
                lambda value, key: {
                    "name": unquote(_.get(value, "vn", "")),
                    "units": _.get(value, "vudm", ""),
                    "readable_name": unquote(_.get(device, f"lng.vrs.{key}.uvun", ""))
                    or _.get(device, f"lng.vrs.{key}.vun", ""),
                    "id": key,
                }
            )
        )
        .value()
    )

    return attributes


def transform_socket_message(
    message: str, devices: list[ClientDevice]
) -> tuple[list[Datapoint], list[Alarm]]:
    """Transform a recieved socket message into attribute values and alarms."""

    data = json.loads(message)

    datapoints: list[Datapoint] = (
        _.chain(data)
        .get("values", [])
        .map_(
            (
                lambda value: {
                    "device": _.get(value, "n", ""),
                    "attribute": _.get(value, "p", ""),
                    "value": _.get(value, "v", ""),
                }
            )
        )
        .map_(
            (
                lambda value: {
                    **value,
                    "device_name": _.get(devices, f"{value['device']}.name"),
                    "readable_attribute_name": _.get(
                        devices,
                        f"{value['device']}.attributes.{value['attribute']}.readable_name",
                    ),
                    "attribute_name": _.get(
                        devices,
                        f"{value['device']}.attributes.{value['attribute']}.name",
                    ),
                }
            )
        )
        .filter_(lambda value: value["attribute_name"])
        .value()
    )

    alarms: list[Alarm] = (
        _.chain(data)
        .get("alrms", [])
        .map_(
            (
                lambda value: {
                    "device": _.get(value, "n", ""),
                    "alarm": _.get(value, "p", ""),
                    "value": _.get(value, "v", ""),
                }
            )
        )
        .filter_(lambda alarm: int(alarm["value"]) > 0)
        .map_(
            (
                lambda value: {
                    **value,
                    "device_name": _.get(devices, f"{value['device']}.name"),
                    "alarm_name": _.get(
                        devices,
                        f"{value['device']}.attributes.{value['alarm']}.readable_name",
                    ),
                    "alarm_code": _.get(
                        devices,
                        f"{value['device']}.attributes.{value['alarm']}.name",
                    ),
                }
            )
        )
        .filter_(lambda value: value["alarm_code"])
        .value()
    )

    return datapoints, alarms


def transform_to_alarms(response: str, devices: list[ClientDevice]) -> list[Alarm]:
    """Extract all current alarms from the HTTP resonse."""

    alarms: list[Alarm] = (
        _.chain(response)
        .get("rows", [])
        .map_(
            (
                lambda value: {
                    "device": _.get(value, "did", ""),
                    "alarm": _.get(value, "vid", ""),
                    "alarm_name": _.get(value, "nm", ""),
                    "start_time": _.get(value, "ds", ""),
                    "end_time": _.get(value, "de", ""),
                }
            )
        )
        .filter_(  # filter for active alarms
            lambda alarm: alarm["end_time"] == "null"
        )
        .map_(
            (
                lambda value: {
                    **value,
                    "device_name": _.get(devices, f"{value['device']}.name"),
                    "alarm_code": _.get(
                        devices,
                        f"{value['device']}.attributes.{value['alarm']}.name",
                    ),
                }
            )
        )
        .filter_(lambda value: value["alarm_code"])
        .value()
    )

    return alarms


def generate_alarms_list(
    alarms: list[Alarm],
    from_socket: bool,
    attr_details: AttributeDetails,
    device_name,
):
    """Generate a list of changes to be applied to the cached alarm values for the specified device"""
    alarms_to_report = {}

    alarm_names = [
        attr["name"]
        for attr in attr_details.values()
        if "is_alarm" in attr and attr["is_alarm"]
    ]

    # The response from polling the alarms endpoint includes all active alarms
    # So, we clear all possible alarms first
    if not from_socket:
        for name in alarm_names:
            alarms_to_report[name] = False

    # Filter only the alarm codes that we are interested in for this device
    dev_alarms = [
        a
        for a in alarms
        if a["alarm_code"] in attr_details and a["device_name"] == device_name
    ]

    for alarm in dev_alarms:
        alarm_code = alarm["alarm_code"]
        attr_name = attr_details[alarm_code]["name"]
        alarms_to_report[attr_name] = True

    return alarms_to_report
