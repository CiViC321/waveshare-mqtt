import json

import pytest

from waveshare_mqtt.config import Settings
from waveshare_mqtt.mqtt_app import MqttRelayApp


class FakeClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, payload, retain))


class FakeController:
    def __init__(self):
        self.flashes = []
        self.modes = []

    def software_version(self):
        return "V2.00"

    def flash_relay(self, channel, duration):
        self.flashes.append((channel, duration))

    def set_relay_mode(self, channel, mode):
        self.modes.append((channel, mode))

    def relay_mode(self, channel):
        return "toggle"


def test_home_assistant_discovery_publishes_eight_switches_and_eight_binary_sensors():
    settings = Settings(mqtt_base_topic="waveshare", mqtt_client_id="test-relay")
    app = MqttRelayApp(FakeController(), settings)
    app.client = FakeClient()

    app.publish_home_assistant_discovery()

    assert len(app.client.published) == 24
    devices = set()
    switch_configs = [item for item in app.client.published if "/switch/" in item[0] and "/config" in item[0]]
    sensor_configs = [item for item in app.client.published if "/binary_sensor/" in item[0] and "/config" in item[0]]
    attributes = [item for item in app.client.published if "/attributes" in item[0]]
    assert len(switch_configs) == 8
    assert len(sensor_configs) == 8
    assert len(attributes) == 8
    for channel, (topic, payload, retained) in enumerate(switch_configs, start=1):
        config = json.loads(payload)
        assert topic == f"homeassistant/switch/test-relay_relay_{channel}/config"
        assert retained is True
        assert config["name"] == f"Relay {channel}"
        assert config["unique_id"] == f"test-relay_relay_{channel}"
        assert config["command_topic"] == f"waveshare/relay/{channel}/set"
        assert config["state_topic"] == f"waveshare/relay/{channel}/state"
        assert config["device"]["sw_version"] == "V2.00"
        assert config["json_attributes_topic"] == f"waveshare/relay/{channel}/attributes"
        devices.add(tuple(config["device"]["identifiers"]))

    for channel, (topic, payload, retained) in enumerate(sensor_configs, start=1):
        config = json.loads(payload)
        assert topic == f"homeassistant/binary_sensor/test-relay_input_{channel}/config"
        assert retained is True
        assert config["name"] == f"Input {channel}"
        assert config["unique_id"] == f"test-relay_input_{channel}"
        assert config["state_topic"] == f"waveshare/input/{channel}/state"
        assert config["payload_on"] == "ON"
        assert config["payload_off"] == "OFF"
        assert config["device"]["sw_version"] == "V2.00"

    for channel, (topic, payload, retained) in enumerate(attributes, start=1):
        assert topic == f"waveshare/relay/{channel}/attributes"
        assert json.loads(payload) == {"relay_control_mode": "toggle"}
        assert retained is True

    assert devices == {("test-relay",)}


def test_flash_command_uses_duration_in_seconds():
    settings = Settings(mqtt_base_topic="waveshare", mqtt_client_id="test-relay")
    controller = FakeController()
    app = MqttRelayApp(controller, settings)

    message = type("Message", (), {
        "topic": "waveshare/relay/3/flash",
        "payload": b"1.5",
        "qos": 0,
        "retain": False,
    })()
    app._on_message(None, None, message)

    assert controller.flashes == [(3, 1.5)]


def test_mode_command_accepts_named_mode():
    settings = Settings(mqtt_base_topic="waveshare", mqtt_client_id="test-relay")
    controller = FakeController()
    app = MqttRelayApp(controller, settings)

    message = type("Message", (), {
        "topic": "waveshare/relay/3/mode",
        "payload": b"toggle",
        "qos": 0,
        "retain": False,
    })()
    app._on_message(None, None, message)

    assert controller.modes == [(3, 2)]


def test_mode_command_rejects_numeric_payload():
    with pytest.raises(ValueError):
        MqttRelayApp._parse_mode("2")
