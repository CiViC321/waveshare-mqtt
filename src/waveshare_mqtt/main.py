"""Command-line entry point."""

from __future__ import annotations

import logging

from .config import Settings
from .hardware import RelayController
from .mqtt_app import MqttRelayApp


def main() -> None:
    settings = Settings.from_environment()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Waveshare MQTT bridge on %s", settings.modbus_port)
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
