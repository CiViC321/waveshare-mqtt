"""Command-line entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waveshare_mqtt.config import Settings
from waveshare_mqtt.hardware import RelayController
from waveshare_mqtt.mqtt_app import MqttRelayApp


def main() -> None:
    settings = Settings.from_environment()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s [%(threadName)s]: %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Waveshare MQTT bridge")
    logger.debug(
        "Configuration: serial=%s slave_id=%d baudrate=%d parity=%s stopbits=%d "
        "relay_register=%d input_register=%d mqtt=%s:%d base_topic=%s "
        "discovery_prefix=%s poll_interval=%.1fs tls=%s",
        settings.modbus_port, settings.modbus_slave_id, settings.modbus_baudrate,
        settings.modbus_parity, settings.modbus_stopbits, settings.relay_start_register,
        settings.input_start_register, settings.mqtt_host, settings.mqtt_port,
        settings.mqtt_base_topic, settings.mqtt_discovery_prefix,
        settings.mqtt_poll_interval, settings.mqtt_tls,
    )
    controller = RelayController.from_serial(
        port=settings.modbus_port,
        slave_id=settings.modbus_slave_id,
        baudrate=settings.modbus_baudrate,
        bytesize=settings.modbus_bytesize,
        parity=settings.modbus_parity,
        stopbits=settings.modbus_stopbits,
        timeout=settings.modbus_timeout,
        relay_start_register=settings.relay_start_register,
        input_start_register=settings.input_start_register,
    )
    MqttRelayApp(controller, settings).run()


if __name__ == "__main__":
    main()
