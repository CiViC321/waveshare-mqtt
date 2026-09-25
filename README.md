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

## Raspberry Pi remote run and debug

Install Raspberry Pi OS, connect the RS485 adapter, and find its device name:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

On the Pi, install Python and the project dependencies:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
git clone git@github.com:CiViC321/waveshare-mqtt.git
cd waveshare-mqtt
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` on the Pi. At minimum, set `MODBUS_PORT` to the adapter path and `MQTT_HOST` to the broker address, for example:

```env
MODBUS_PORT=/dev/ttyUSB0
MQTT_HOST=192.168.1.10
LOG_LEVEL=DEBUG
```

Add the Pi user to the serial-device group, then log out and back in:

```bash
sudo usermod -aG dialout "$USER"
```

Run the service directly:

```bash
source .venv/bin/activate
python -m waveshare_mqtt.main
```

For interactive remote debugging, install the VS Code **Remote - SSH** and **Python** extensions on your computer. Connect to the Pi with Remote-SSH, open the cloned project folder on the Pi, select `.venv/bin/python` as the interpreter, and press `F5` using the `Debug Waveshare MQTT` profile. Set breakpoints in `main.py`, `mqtt_app.py`, or `hardware.py`. The debugger and code execute on the Pi, so the RS485 adapter remains local to the Pi.

For unattended operation on the Pi, use Docker Compose instead. Set `MODBUS_PORT=/dev/ttyUSB0` in `.env`, then run:

```bash
RS485_DEVICE=/dev/ttyUSB0 docker compose up -d --build
docker compose logs -f waveshare-mqtt
```

## Docker

### Automatic Docker Hub publishing

GitHub Actions builds and publishes the image after every push to `main`. It also supports manual runs from the repository's **Actions** tab. Before the first run, add these repository secrets under **Settings > Secrets and variables > Actions**:

```text
DOCKERHUB_USERNAME = your Docker Hub username
DOCKERHUB_TOKEN = a Docker Hub access token
```

The Docker Hub repository must be `civic321/waveshare-mqtt`, or update `IMAGE_NAME` in `.github/workflows/docker-publish.yml`. Successful builds publish `latest` and a commit-specific tag.

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
