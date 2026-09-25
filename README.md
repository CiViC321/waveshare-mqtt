# Waveshare Modbus MQTT Bridge

A small Python service for controlling a Waveshare Modbus RTU 8-channel relay module (D) with digital inputs over RS485. It uses [Paho MQTT](https://eclipse.dev/paho/) and [MinimalModbus](https://minimalmodbus.readthedocs.io/).

## Install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
Copy-Item .env.example .env
```

Edit `.env` for the serial port and MQTT broker, then run:

```powershell
waveshare-mqtt
# or: python -m waveshare_mqtt.main
```

Set `LOG_LEVEL=DEBUG` for Modbus and MQTT diagnostics.

## Docker

On a Linux host with the RS485 adapter available as `/dev/ttyUSB0`:

```bash
cp .env.example .env
# Set MQTT_HOST and other device settings in .env.
docker compose up -d --build
docker compose logs -f waveshare-mqtt
```

To use another serial device, set `RS485_DEVICE` before starting Compose:

```bash
RS485_DEVICE=/dev/ttyACM0 docker compose up -d --build
```

The Compose file maps that host device into the container and overrides `MODBUS_PORT` with the container path. Docker Desktop on Windows does not generally expose a local COM port through the Linux container device mapping; use a Linux host, a USB-over-IP/serial gateway, or configure the RS485 adapter through a network-accessible service.

## MQTT topics

Commands accept `ON`, `OFF`, `1`, `0`, `true`, `false`, `high`, or `low`:

| Topic | Direction | Meaning |
| --- | --- | --- |
| `waveshare/relay/1/set` | MQTT to device | Set relay channel 1 |
| `waveshare/relay/all/set` | MQTT to device | Set all eight relays |
| `waveshare/relay/1/state` | Device to MQTT | Retained relay state |
| `waveshare/input/1/state` | Device to MQTT | Retained digital input state |

Replace `waveshare/relay` with `MQTT_BASE_TOPIC` when configured. Relay and input channels are numbered 1 through 8 in MQTT topics; Modbus register offsets are zero-based by default.

When the MQTT connection is established, the bridge publishes retained Home Assistant MQTT Discovery configuration under `MQTT_DISCOVERY_PREFIX` (default `homeassistant`). Home Assistant will create eight switches grouped under one device named `Waveshare 8-Channel Relay`.

## Hardware assumptions

The defaults follow the module's typical Modbus mapping: relay coils at offset 0, digital inputs at offset 0, relay writes via function 05, relay reads via function 01, and input reads via function 02. If the label/manual for your module revision specifies different offsets, set `MODBUS_RELAY_START_REGISTER` and `MODBUS_INPUT_START_REGISTER`.

RS485 wiring should be A-to-A, B-to-B, and shared signal ground where required by the converter. Confirm the module's slave ID, baud rate, parity, and termination before connecting power.

## Test

```powershell
python -m pytest
```
