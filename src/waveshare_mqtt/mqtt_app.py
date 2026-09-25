"""MQTT application layer and topic handling."""

from __future__ import annotations

import logging
import json
import threading
from typing import Any

import paho.mqtt.client as mqtt

from .config import Settings
from .hardware import RelayController

logger = logging.getLogger(__name__)


class MqttRelayApp:
    def __init__(self, controller: RelayController, settings: Settings):
        self.controller = controller
        self.settings = settings
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=settings.mqtt_client_id)
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        if settings.mqtt_tls:
            self.client.tls_set()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._stop_event = threading.Event()
        logger.debug("MQTT client initialized client_id=%s tls=%s", settings.mqtt_client_id, settings.mqtt_tls)

    def run(self) -> None:
        logger.info("Connecting to MQTT broker %s:%d", self.settings.mqtt_host, self.settings.mqtt_port)
        self.client.connect(self.settings.mqtt_host, self.settings.mqtt_port, self.settings.mqtt_keepalive)
        logger.debug("Starting MQTT network loop")
        self.client.loop_start()
        try:
            while not self._stop_event.wait(self.settings.mqtt_poll_interval):
                self.publish_states()
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self._stop_event.set()
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT bridge stopped")

    def stop(self) -> None:
        self._stop_event.set()

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if reason_code != 0:
            logger.error("MQTT connection failed: %s", reason_code)
            return
        logger.debug("MQTT connected reason_code=%s flags=%s", reason_code, flags)
        topic = f"{self.settings.mqtt_base_topic}/relay/+/set"
        client.subscribe(topic)
        client.subscribe(f"{self.settings.mqtt_base_topic}/relay/all/set")
        logger.info("Connected to MQTT; subscribed to %s", topic)
        self.publish_home_assistant_discovery()
        self.publish_states()

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        topic = message.topic
        payload = message.payload.decode("utf-8", errors="replace").strip().lower()
        logger.debug("MQTT message received topic=%s qos=%d retain=%s", topic, message.qos, message.retain)
        prefix = f"{self.settings.mqtt_base_topic}/relay/"
        suffix = "/set"
        try:
            target = topic[len(prefix):-len(suffix)]
            enabled = self._parse_state(payload)
            if target == "all":
                for channel in range(1, RelayController.CHANNELS + 1):
                    self.controller.set_relay(channel, enabled)
            else:
                self.controller.set_relay(int(target), enabled)
            logger.info("Set relay target=%s enabled=%s", target, enabled)
            self.publish_states()
        except (ValueError, IndexError) as exc:
            logger.warning("Ignoring invalid MQTT command topic=%s payload=%r: %s", topic, payload, exc)
        except Exception:
            logger.exception("Relay command failed for topic=%s", topic)

    def publish_states(self) -> None:
        try:
            for channel, state in enumerate(self.controller.relay_states(), start=1):
                self._publish(self._topic("relay", channel, "state"), "ON" if state else "OFF")
            for channel, state in enumerate(self.controller.input_states(), start=1):
                self._publish(self._topic("input", channel, "state"), "ON" if state else "OFF")
            logger.debug("Published relay and input states")
        except Exception:
            logger.exception("Failed to publish Modbus state")

    def publish_home_assistant_discovery(self) -> None:
        """Publish retained MQTT Discovery configs for all relay channels."""
        device = {
            "identifiers": [self.settings.mqtt_client_id],
            "name": "Waveshare 8-Channel Relay",
            "manufacturer": "Waveshare",
            "model": "Modbus RTU 8-CH Relay Module (D)",
        }
        for channel in range(1, RelayController.CHANNELS + 1):
            unique_id = f"{self.settings.mqtt_client_id}_relay_{channel}"
            payload = {
                "name": f"Relay {channel}",
                "unique_id": unique_id,
                "command_topic": self._topic("relay", channel, "set"),
                "state_topic": self._topic("relay", channel, "state"),
                "payload_on": "ON",
                "payload_off": "OFF",
                "state_on": "ON",
                "state_off": "OFF",
                "device": device,
            }
            topic = f"{self.settings.mqtt_discovery_prefix}/switch/{unique_id}/config"
            self._publish(topic, json.dumps(payload))
        logger.info("Published Home Assistant discovery for %d relays", RelayController.CHANNELS)

    def _publish(self, topic: str, payload: str) -> None:
        result = self.client.publish(topic, payload, retain=True)
        if result is not None and result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("MQTT publish failed topic=%s rc=%s", topic, result.rc)
        else:
            logger.debug("MQTT publish queued topic=%s retain=true", topic)

    def _topic(self, kind: str, channel: int, name: str) -> str:
        return f"{self.settings.mqtt_base_topic}/{kind}/{channel}/{name}"

    @staticmethod
    def _parse_state(payload: str) -> bool:
        payload = payload.strip().lower()
        if payload in {"on", "1", "true", "high"}:
            return True
        if payload in {"off", "0", "false", "low"}:
            return False
        raise ValueError("payload must be ON/OFF, 1/0, true/false, or high/low")
