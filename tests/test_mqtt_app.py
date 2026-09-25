import json

from waveshare_mqtt.config import Settings
from waveshare_mqtt.mqtt_app import MqttRelayApp


class FakeClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, payload, retain))


class FakeController:
    pass


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
        devices.add(tuple(config["device"]["identifiers"]))

    assert devices == {("test-relay",)}
