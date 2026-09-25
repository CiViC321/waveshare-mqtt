"""MinimalModbus adapter for the Waveshare 8-channel relay module."""

from __future__ import annotations

import logging
from typing import Protocol

import minimalmodbus

logger = logging.getLogger(__name__)


class Instrument(Protocol):
    def write_bit(self, register: int, value: int, functioncode: int = 5) -> None: ...
    def read_bits(self, register: int, number_of_bits: int, functioncode: int = 1) -> list[int]: ...


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

    @classmethod
    def _validate_channel(cls, channel: int) -> None:
        if not 1 <= channel <= cls.CHANNELS:
            raise ValueError(f"channel must be between 1 and {cls.CHANNELS}, got {channel}")
