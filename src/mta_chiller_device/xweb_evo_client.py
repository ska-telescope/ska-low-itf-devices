"""This module contains the code that directly interfaces to the XWeb Evo online platform."""

from datetime import datetime, timedelta

import pydash as _
import requests
from websockets import ClientConnection
from websockets.sync.client import connect

from mta_chiller_device.custom_types import Alarm, ClientDevice, ControlGroup

from . import utils


class XWebEvoClient:
    """A Python client for communicating with the XWeb Evo chiller user interface."""

    def __init__(self, ip: str, username: str, hashed_password: str):
        self.ip: str = ip
        self.base_url: str = f"http://{self.ip}"
        self.username: str = username
        self.hashed_password: str = hashed_password
        self._sses: str | None = None
        self._command_plgid: str | None = None
        self._socket: ClientConnection | None = None
        self.control_groups: list[ControlGroup] = []
        self.devices: list[ClientDevice] = []

    def start(self):
        """Open communication to the XWeb Evo platform."""

        self.login()
        self.load_config()
        self.open_socket()

    def close(self):
        """Close the web socket and clears the session string."""

        self._sses = None
        self.close_socket()

    def login(self):
        """Log into the XWeb Evo system to obtain authentication credentials."""

        url = f"{self.base_url}/cgi-bin/xwmanager.lua"
        data = {
            "uname": self.username,
            "upass": self.hashed_password,
            "r": "l",
        }

        response = requests.post(url, data=data, timeout=60)
        response.raise_for_status()

        # Check that we do not have an error response
        if response.text.strip() == '{"error":1}':
            raise ValueError("Incorrect login details")

        self._sses, self._command_plgid = utils.transform_to_credentials(
            response.json()
        )

    def maintain_session(self):
        """Keep the XWeb Evo login session active."""

        assert self._sses, "The client must be logged in first"

        url = f"{self.base_url}/cgi-bin/xwsses.cgi"
        data = {
            "op": "4",
            "sses": self._sses,
        }

        response = requests.post(url, data=data, timeout=60)
        response.raise_for_status()

        # Check that we do not have an error response
        if response.text.strip() != '({"e":0})':
            raise ValueError("Unable to maintain the session")

    def open_socket(self):
        """Open the websocket connection with the XWeb Evo system."""

        self._socket = connect(f"ws://{self.ip}/evocli", origin=self.base_url)

    def close_socket(self):
        """Close the websocket connection with the XWeb Evo system."""

        self._socket.close()

    def recieve_socket(self):
        """Wait for and receives a single websocket message."""

        message = self._socket.recv(timeout=60)
        return utils.transform_socket_message(message, self.devices)

    def load_config(self):
        """Load the system configuration (chillers, commands, etc.) from the XWeb Evo platform."""

        assert self._sses, "The client must be logged in first"

        url = f"{self.base_url}/cgi-bin/getsetup.lua"
        data = {
            "ln": "en-GB",
            "SSES": self._sses,
        }

        response = requests.post(url, data=data, timeout=60)
        response.raise_for_status()

        # Check that we do not have an error response
        if response.text.strip() == '{"status":"2"}':
            raise ValueError("Failed to load setup configuraion")

        self.control_groups, self.devices = utils.transform_to_config(response.json())

    def get_alarms(self) -> list[Alarm]:
        """Load any active alarms from the XWeb Evo platform."""

        assert self._sses, "The client must be logged in first"

        time_delta = timedelta(days=-7)
        start_time = (datetime.now() + time_delta).strftime("%Y%m%d%H%M00")
        end_time = datetime.now().strftime("%Y%m%d%H%M00")

        url = f"{self.base_url}/cgi-bin/xwalmlog.cgi"
        data = {
            "SSES": self._sses,
            "SRV": 1,
            "Q": (
                '{"lvl":-1,"cat":-1,"typ":-1,"dev":-1,"usr":-1,"ntf":-1,"active":-1,'
                + f'"st":{start_time},"et":{end_time}'
                + "}"
            ),
        }

        response = requests.post(url, data=data, timeout=60)
        response.raise_for_status()

        if response.text.strip() == "({})":
            raise ValueError("Failed to load alarms")

        return utils.transform_to_alarms(response.json(), self.devices)

    def send_command(self, device_id: str, command_id: str):
        """Send the specified command to the XWeb Evo system."""

        assert self._sses, "The client must be logged in first"
        assert self._command_plgid, "Invalid command authentication"

        url = f"{self.base_url}/cgi-bin/devcmd.cgi"
        data = {
            "sses": self._sses,
            "plgid": self._command_plgid,
            "D_0": device_id,
            "C_0": command_id,
        }

        response = requests.post(url, data=data, timeout=60)
        response.raise_for_status()

        # check response for errors
        if _.get(response.json(), "devcmd[0].er") != 0:
            raise ValueError("The requested command reported an error")

    def lookup_command(self, device_id: str, name: str) -> str:
        """Return the command ID for a given command name/readable code."""

        command_id: str = (
            _.chain(self.devices)
            .get(f"{device_id}.commands", {})
            .values()
            .find({"name": name})
            .value()
        )["id"]

        return command_id

    def lookup_device(self, name: str) -> str:
        """Return the chiller ID for a given chiller name."""

        device_id: str = (_.chain(self.devices).values().find({"name": name}).value())[
            "id"
        ]

        return device_id
