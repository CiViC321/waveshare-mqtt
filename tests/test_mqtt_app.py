import json

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

    def software_version(self):
        return "V2.00"

    def flash_relay(self, channel, duration):
        self.flashes.append((channel, duration))


def test_home_assistant_discovery_publishes_eight_switches():
    settings = Settings(mqtt_base_topic="waveshare", mqtt_client_id="test-relay")
    app = MqttRelayApp(FakeController(), settings)
    app.client = FakeClient()

    app.publish_home_assistant_discovery()

    assert len(app.client.published) == 8
    devices = set()
    for channel, (topic, payload, retained) in enumerate(app.client.published, start=1):
        config = json.loads(payload)
        assert topic == f"homeassistant/switch/test-relay_relay_{channel}/config"
        assert retained is True
        assert config["name"] == f"Relay {channel}"
        assert config["unique_id"] == f"test-relay_relay_{channel}"
        assert config["command_topic"] == f"waveshare/relay/{channel}/set"
        assert config["state_topic"] == f"waveshare/relay/{channel}/state"
        assert config["device"]["sw_version"] == "V2.00"
        devices.add(tuple(config["device"]["identifiers"]))

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
