"""Thi module uses the XWeb Evo client to control and monitor the chiller system."""

from threading import Event, Thread

from requests import RequestException
from websockets import ConnectionClosed, WebSocketException

from mta_chiller_device.custom_types import (
    Alarm,
    AttributeCallback,
    AttributeDetails,
    ClientConfig,
    CommunicationStateCallback,
    ComponentStateCallback,
    Datapoint,
)
from mta_chiller_device.xweb_evo_client import XWebEvoClient


class MTAChillerManager:
    """A class to monitor and control the MTA chillers."""

    def __init__(
        self,
        client_config: ClientConfig,
        device_name: str,
        update_communication_state: CommunicationStateCallback,
        update_component_state: ComponentStateCallback,
        update_attribute: AttributeCallback,
        *,
        alarm_polling_period: int = 60,
    ):
        # Create the XWeb client
        self._client = XWebEvoClient(**client_config)
        self._device_name = device_name

        # Store the callback functions
        self._update_communication_state = update_communication_state
        self._update_component_state = update_component_state
        self._update_attribute = update_attribute

        # Variables for threading
        self._thread = None
        self._shutdown_event = Event()
        self._alarm_polling_period = alarm_polling_period

        self._attribute_details: AttributeDetails = {
            # Client variable name: Tango attribute information
            "Pb1_°C_bar": {
                "name": "tank_outlet_temp",
                "format_fn": float,
            },
            "Pb2_°C_bar": {
                "name": "evaporator_outlet_temp",
                "format_fn": float,
            },
            "ChillerSetpoint_°C_bar": {
                "name": "set_point",
                "format_fn": float,
            },
            "Chiller_st": {
                "name": "chiller_state",
                "format_fn": self._int_to_bool,
            },
            "Compressor1": {
                "name": "compressor_state",
                "format_fn": self._int_to_bool,
            },
            "EvapWtPm_SupFan": {
                "name": "water_pump_state",
                "format_fn": self._int_to_bool,
            },
            # Alarms:
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
            "EvapFlowSwitch": {
                "name": "evaporator_flow_switch_alarm",
                "is_alarm": True,
            },
            "GeneralAlarm1": {
                "name": "general_phase_monitor_alarm",
                "is_alarm": True,
            },
            "HighPresSwtCir1": {
                "name": "high_pressure_switch_alarm",
                "is_alarm": True,
            },
            "LowPresSwtCir1": {
                "name": "low_pressure_switch_alarm",
                "is_alarm": True,
            },
            "No-Link": {
                "name": "chiller_disconnected_alarm",
                "is_alarm": True,
            },
            "Probe1Alarm": {
                "name": "probe_1_alarm",
                "is_alarm": True,
            },
            "Probe2Alarm": {
                "name": "probe_2_alarm",
                "is_alarm": True,
            },
        }

        # Create a local cache of attribute values
        self._attribute_cache: dict[str, int | float | bool | None] = {}

        for attr in self._attribute_details.values():
            self._attribute_cache[attr["name"]] = None

    def start_communicating(self):
        """Begin communication with the chillers."""

        # The chiller system has only one power level,
        # so should have state ON once communication has been established
        if self._thread is not None:
            return  # We are already trying to connect

        self._thread = Thread(target=self._monitor)
        self._shutdown_event.clear()
        self._thread.start()
        self._update_communication_state("NOT_ESTABLISHED")

    def stop_communicating(self):
        """Close communication with the chillers."""

        self._shutdown_event.set()
        self._thread.join()  # wait for the thread to terminate
        self._client.close()
        self._update_communication_state("DISABLED")

    def get_attribute_value(self, attr_name: str):
        """Return the last reported value for the specified attribute."""

        return self._attribute_cache[attr_name]

    #### COMMANDS ####

    def chiller_on(self):
        """Turn on the specified chiller."""

        self._send_command("Chiller")

    def chiller_off(self):
        """Turn off the specified chiller."""

        self._send_command("Stand_by")

    def alarm_mute(self):
        """Mute the alarms for the specified chiller."""

        self._send_command("AlarmMute")

    def alarm_reset(self):
        """Reset the alarms for the specified chiller."""

        self._send_command("AlarmReset")

    #### HELPER FUNCTIONS ####

    def _monitor(self):
        # Set the event to trigger the initial connection
        reconnect_event = Event()
        reconnect_event.set()
        # Create a thread to handle the websocket connection
        socket_thread = Thread(target=self._receive_socket, args=(reconnect_event,))
        socket_thread.start()

        while not self._shutdown_event.is_set():
            # Check the status of the connection
            if reconnect_event.is_set():
                # restart our connection to the client
                try:
                    print("(Re)Connecting the client")
                    self._client.start()
                    self._update_communication_state("ESTABLISHED")
                    self._update_component_state(power="ON")
                    reconnect_event.clear()

                    # check for alarms
                    alarms = self._client.get_alarms()
                    self._process_new_alarms(alarms)

                except (
                    RequestException,
                    ValueError,
                    WebSocketException,
                    AssertionError,
                ) as e:
                    print(f"Unable to connect: {e}")
                    reconnect_event.set()

            else:
                try:
                    # maintain the session
                    self._client.maintain_session()
                    print("Maintained session")

                    # check for alarms
                    alarms = self._client.get_alarms()
                    self._process_new_alarms(alarms)

                except (RequestException, ValueError) as e:
                    print(f"Encountered an exception: {e}")
                    self._update_communication_state("NOT_ESTABLISHED")
                    reconnect_event.set()

            # wait for 1 minute
            self._shutdown_event.wait(timeout=self._alarm_polling_period)

        # Close the client
        socket_thread.join()  # wait for the thread to terminate
        self._client.close()

    def _receive_socket(self, reconnect_event: Event):
        while not self._shutdown_event.is_set():
            if not reconnect_event.is_set():
                # wait for new attributes over Websockets
                try:
                    datapoints, alarms = self._client.recieve_socket()

                    for datapoint in datapoints:
                        self._process_new_datapoint(datapoint)

                    self._process_new_alarms(alarms, True)

                except ConnectionClosed:
                    print("Socket connection was closed")
                    self._update_communication_state("NOT_ESTABLISHED")
                    reconnect_event.set()

    def _process_new_datapoint(self, datapoint: Datapoint):
        if datapoint["device_name"] == self._device_name:
            if datapoint["attribute_name"] in self._attribute_details:
                attribute_details = self._attribute_details[datapoint["attribute_name"]]

                tango_name = attribute_details["name"]
                formatted_value = attribute_details["format_fn"](datapoint["value"])

                self._attribute_cache[tango_name] = formatted_value
                self._update_attribute(tango_name, formatted_value)

    def _process_new_alarms(self, alarms: list[Alarm], from_socket=False):
        alarms_to_report = {}

        # If we are looking at the response from polling the alarms endpoint
        # we will clear any active alarms first
        if not from_socket:
            attr_names = [
                a["name"]
                for a in self._attribute_details.values()
                if "is_alarm" in a and a["is_alarm"]
            ]

            for name in attr_names:
                alarms_to_report[name] = False

        # Filter only the alarm codes that we are interested in for this device
        dev_alarms = [
            a
            for a in alarms
            if a["alarm_code"] in self._attribute_details
            and a["device_name"] == self._device_name
        ]

        for alarm in dev_alarms:
            alarm_code = alarm["alarm_code"]
            attr_name = self._attribute_details[alarm_code]["name"]
            alarms_to_report[attr_name] = True

        # Update the alarm attributes
        for attr_name, val in alarms_to_report.items():
            self._attribute_cache[attr_name] = val
            self._update_attribute(attr_name, val, in_alarm=val)

    def _send_command(self, command: str):
        # get the chiller id
        device_id = self._client.lookup_device(self._device_name)
        # get the command id
        command_id = self._client.lookup_command(device_id, command)
        # issue the command
        try:
            self._client.send_command(device_id, command_id)
        except (RequestException, ValueError) as e:
            print(
                f"Failed to send command: device {device_id}, command {command_id}, {e}"
            )

    def _int_to_bool(self, val: str):
        return bool(int(val))
