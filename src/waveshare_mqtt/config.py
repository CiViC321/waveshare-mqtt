"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    modbus_port: str = "COM3"
    modbus_slave_id: int = 1
    modbus_baudrate: int = 9600
    modbus_bytesize: int = 8
    modbus_parity: str = "N"
    modbus_stopbits: int = 1
    modbus_timeout: float = 1.0
    relay_start_register: int = 0
    input_start_register: int = 0
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_keepalive: int = 60
    mqtt_client_id: str = "waveshare-relay-1"
    mqtt_base_topic: str = "waveshare"
    mqtt_discovery_prefix: str = "homeassistant"
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_tls: bool = False
    mqtt_poll_interval: float = 5.0
    log_level: str = "INFO"

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        values = {field.name: getattr(cls, field.name) for field in cls.__dataclass_fields__.values()}
        converters = {
            "modbus_slave_id": int, "modbus_baudrate": int, "modbus_bytesize": int,
            "modbus_stopbits": int, "modbus_timeout": float, "relay_start_register": int,
            "input_start_register": int, "mqtt_port": int, "mqtt_keepalive": int,
            "mqtt_poll_interval": float,
        }
        env_names = {
            field: field.upper() for field in values
        }
        for field, default in values.items():
            raw = os.getenv(env_names[field])
            if raw is None:
                continue
            if field in converters:
                values[field] = converters[field](raw)
            elif isinstance(default, bool):
                values[field] = raw.strip().lower() in {"1", "true", "yes", "on"}
            else:
                values[field] = raw
        return cls(**values)
