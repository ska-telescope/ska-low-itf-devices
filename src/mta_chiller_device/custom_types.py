from collections.abc import Callable
from typing import Optional, TypedDict, TypeAlias


class AttributeDetail(TypedDict):
    name: str
    format_fn: Callable[[str], int | float | str] | None
    is_alarm: bool | None


AttributeDetails: TypeAlias = dict[str, AttributeDetail]


class Datapoint(TypedDict):
    device: str
    attribute: str
    value: str
    device_name: str
    readable_attribute_name: str
    attribute_name: str


class Alarm(TypedDict):
    device: str
    alarm: str
    device_name: str
    alarm_name: str
    alarm_code: str
    value: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]


class ClientCommand(TypedDict):
    name: str
    readable_name: str
    id: str


class ClientAttribute(TypedDict):
    name: str
    units: str
    readable_name: str
    id: str


class ClientDevice(TypedDict):
    address: str
    description: str
    name: str
    model: str
    commands: list[ClientCommand]
    attributes: list[ClientAttribute]
    id: str


class ControlGroup(TypedDict):
    name: str
    devices: list[int]
    id: str


class ClientConfig(TypedDict):
    ip: str
    username: str
    hashed_password: str


class ManagerDevice(TypedDict):
    tango_prefix: str
    chiller_num: int
    device_name: str


CommunicationStateCallback: TypeAlias = Callable[[str | None, bool | None], None]
ComponentStateCallback: TypeAlias = Callable[[str], None]
AttributeCallback: TypeAlias = Callable[[str, int | float | bool, bool | None], None]
