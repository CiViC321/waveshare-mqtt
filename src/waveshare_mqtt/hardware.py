"""MinimalModbus adapter for the Waveshare 8-channel relay module."""

from __future__ import annotations

import logging
import struct
from typing import Protocol

import minimalmodbus

logger = logging.getLogger(__name__)


class Instrument(Protocol):
    def write_bit(self, register: int, value: int, functioncode: int = 5) -> None: ...
    def write_register(self, register: int, value: int, functioncode: int = 6) -> None: ...
    def read_bits(self, register: int, number_of_bits: int, functioncode: int = 1) -> list[int]: ...
    def read_register(self, register: int, number_of_decimals: int = 0,
                      functioncode: int = 3, signed: bool = False) -> int: ...
    def _perform_command(self, functioncode: int, payload_to_slave: bytes) -> bytes: ...


class RelayController:
    CHANNELS = 8

    def __init__(self, instrument: Instrument, relay_start_register: int = 0, input_start_register: int = 0):
        self.instrument = instrument
        self.relay_start_register = relay_start_register
        self.input_start_register = input_start_register

    @classmethod
    def from_serial(cls, port: str, slave_id: int, baudrate: int, bytesize: int,
                    parity: str, stopbits: int, timeout: float, relay_start_register: int = 0,
                    input_start_register: int = 0) -> "RelayController":
        instrument = minimalmodbus.Instrument(port, slave_id, mode=minimalmodbus.MODE_RTU)
        instrument.serial.baudrate = baudrate
        instrument.serial.bytesize = bytesize
        instrument.serial.parity = parity
        instrument.serial.stopbits = stopbits
        instrument.serial.timeout = timeout
        instrument.clear_buffers_before_each_transaction = True
        logger.info("Configured Modbus RTU port=%s slave_id=%d", port, slave_id)
        logger.debug(
            "Modbus serial settings baudrate=%d bytesize=%d parity=%s stopbits=%d timeout=%.2fs",
            baudrate, bytesize, parity, stopbits, timeout,
        )
        return cls(instrument, relay_start_register, input_start_register)

    def set_relay(self, channel: int, enabled: bool) -> None:
        self._validate_channel(channel)
        register = self.relay_start_register + channel - 1
        logger.debug("Writing relay channel=%d register=%d enabled=%s", channel, register, enabled)
        self.instrument.write_bit(register, int(enabled), functioncode=5)
        logger.debug("Relay write completed channel=%d", channel)

    def set_relay_mode(self, channel: int, mode: int) -> None:
        self._validate_channel(channel)
        if not 0 <= mode <= 3:
            raise ValueError("relay mode must be between 0 and 3")

        register = 0x1000 + channel - 1
        logger.debug("Writing relay mode channel=%d register=%d mode=%d", channel, register, mode)
        self.instrument.write_register(register, mode, functioncode=6)

    def relay_mode(self, channel: int) -> str:
        self._validate_channel(channel)
        register = 0x1000 + channel - 1
        mode = self.instrument.read_register(register, functioncode=3, signed=False)
        mode_name = self.mode_name(mode)
        logger.debug("Read relay mode channel=%d mode=%s", channel, mode_name)
        return mode_name

    def flash_relay(self, channel: int, duration_seconds: float) -> None:
        self._validate_channel(channel)
        if duration_seconds <= 0:
            raise ValueError("duration must be greater than zero")

        duration_units = round(duration_seconds * 10)
        if not 1 <= duration_units <= 0x7FFF:
            raise ValueError("duration must be between 0.1 and 3276.7 seconds")

        register = 0x0200 + channel - 1
        payload = struct.pack(">HH", register, duration_units)
        logger.debug(
            "Flashing relay channel=%d register=%d duration=%.1fs",
            channel, register, duration_units / 10,
        )
        self.instrument._perform_command(5, payload)

    def relay_states(self) -> list[bool]:
        logger.debug("Reading relay states from register=%d", self.relay_start_register)
        values = self.instrument.read_bits(self.relay_start_register, self.CHANNELS, functioncode=1)
        states = [bool(value) for value in values]
        logger.debug("Relay states read: %s", states)
        return states

    def input_states(self) -> list[bool]:
        logger.debug("Reading digital inputs from register=%d", self.input_start_register)
        values = self.instrument.read_bits(self.input_start_register, self.CHANNELS, functioncode=2)
        states = [bool(value) for value in values]
        logger.debug("Digital input states read: %s", states)
        return states

    def software_version(self) -> str:
        """Read and format the device software version from register 0x8000."""
        raw_version = self.instrument.read_register(0x8000, functioncode=3, signed=False)
        version = f"V{raw_version // 100}.{raw_version % 100:02d}"
        logger.debug("Device software version read: %s", version)
        return version

    @classmethod
    def _validate_channel(cls, channel: int) -> None:
        if not 1 <= channel <= cls.CHANNELS:
            raise ValueError(f"channel must be between 1 and {cls.CHANNELS}, got {channel}")

    @staticmethod
    def mode_name(mode: int) -> str:
        names = {0: "normal", 1: "linkage", 2: "toggle", 3: "edge"}
        try:
            return names[mode]
        except KeyError as exc:
            raise ValueError(f"unsupported relay mode value: {mode}") from exc
