from waveshare_mqtt.hardware import RelayController


class FakeInstrument:
    def __init__(self):
        self.writes = []
        self.register_reads = []
        self.commands = []

    def write_bit(self, register, value, functioncode=5):
        self.writes.append((register, value, functioncode))

    def read_bits(self, register, number_of_bits, functioncode=1):
        assert number_of_bits == 8
        assert functioncode in (1, 2)
        return [1, 0, 1, 0, 0, 1, 0, 1]

    def read_register(self, register, number_of_decimals=0, functioncode=3, signed=False):
        self.register_reads.append((register, number_of_decimals, functioncode, signed))
        return 200

    def _perform_command(self, functioncode, payload_to_slave):
        self.commands.append((functioncode, payload_to_slave))
        return payload_to_slave


def test_set_relay_uses_one_based_channel_and_function_05():
    instrument = FakeInstrument()
    controller = RelayController(instrument, relay_start_register=10)

    controller.set_relay(3, True)

    assert instrument.writes == [(12, 1, 5)]


def test_reads_return_eight_boolean_states():
    controller = RelayController(FakeInstrument())

    assert controller.relay_states() == [True, False, True, False, False, True, False, True]
    assert controller.input_states() == [True, False, True, False, False, True, False, True]


def test_reads_and_formats_device_software_version():
    instrument = FakeInstrument()
    controller = RelayController(instrument)

    assert controller.software_version() == "V2.00"
    assert instrument.register_reads == [(0x8000, 0, 3, False)]


def test_flash_relay_uses_native_flash_on_command():
    instrument = FakeInstrument()
    controller = RelayController(instrument)

    controller.flash_relay(3, 0.7)

    assert instrument.commands == [(5, b"\x02\x02\x00\x07")]


def test_invalid_channel_is_rejected():
    controller = RelayController(FakeInstrument())

    try:
        controller.set_relay(9, True)
    except ValueError as exc:
        assert "between 1 and 8" in str(exc)
    else:
        raise AssertionError("expected ValueError")
