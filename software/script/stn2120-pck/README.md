# STN2120 Python Package

`stn2120-pck` provides a Python interface for interacting with STN2120-based OBD-II boards, wrapping serial communication, CAN bus helpers, and TCP socket utilities used to bridge diagnostic tools with in-vehicle networks. The package is organised as a standard module that can be installed with `setup.py` and reused in automation or diagnostics workflows.

## Package layout

- `stn2120/stn2120.py` – High-level façade exposing the `Board` class that manages adapter discovery, session initialisation, command dispatching, CAN monitoring, and lifecycle management. It builds on `ic_config.STN2120` for the low-level interactions and utilities from `utils`.
- `stn2120/ic_config.py` – Low-level driver for the STN2120 chipset that configures serial ports, negotiates protocols, toggles CAN monitoring modes, and implements continuous CAN frame reading loops shared by the board helper. It includes socket helpers for vehicle/diagnostic roles and protocol constants.
- `stn2120/commands.py` – Catalogue of ST command definitions exposed as `STNCommand` objects for baud-rate tuning, CAN monitoring, filtering, power-saving, and GPIO management on the adapter.
- `stn2120/network/` – Socket client/server utilities (`netcom.py`) that stream CAN frames or commands between diagnostic and vehicle endpoints over TCP, using blocking queues for framing.
- `stn2120/utils.py` – Shared helpers for serial port discovery, byte/bit manipulation, and adapter status tracking (`OBDStatus`).
- `stn2120/frames.py` and `protocols/` – Message templates and protocol descriptors leveraged by `ic_config.STN2120` during adapter initialisation and CAN decoding.

## Dependencies

The runtime stack relies on:

- [`pyserial`](https://pyserial.readthedocs.io/) for serial port access and `serial.serial_for_url` handling of USB/virtual adapters.
- `redis` for publishing CAN frames when integrating with external data sinks (imported in `ic_config.py`).
- Python standard library modules such as `logging`, `queue`, `threading`, `socket`, and `datetime` for diagnostics, buffering, and TCP networking.

Install these dependencies via `pip install -r requirements.txt` or let `pip` resolve them when installing the package.

## Usage examples

### Board initialisation and discovery

```python
from stn2120 import stn2120

# Discover STN2120 endpoints automatically and start a diagnostic session
board = stn2120.Board(
    portdev=None,              # autodetect read/write serial ports
    baudrate=2000000,
    protocol="31",            # ISO 15765-4 11-bit 500 kbit/s CAN
    role="clt_diag",          # diagnostic client role (vs. "clt_car")
    timeout=0.1,
)
print(board.status())          # -> "Car Connected" once the vehicle responds
```

`Board` validates the role, resolves available serial ports via `utils.scan_serial`, and hands the connection to `ic_config.STN2120` which configures echo, headers, adaptive timing, and CAN monitoring (`STCMM 1`).

### Sending commands and reading CAN traffic

```python
# Issue an ST/AT command and print the parsed response
board.send_cmd("ATRV")

# Enter continuous CAN monitoring mode (STMA) and consume frames
board.read_can_bus()
```

`Board.send_cmd` forwards ASCII commands to `STN2120.send_and_parse`, while `Board.read_can_bus` streams frames emitted by `STN2120.read_can_bus`, handling buffer overflows and re-arming the STMA monitor as needed.

### Networking utilities

Use the TCP client and server helpers to forward CAN frames between a diagnostic workstation and the vehicle gateway:

```python
from stn2120.network import netcom

# Diagnostic side client
client = netcom.socket_clients(("192.168.1.82", 5555))
client.send_data(frame_bytes, len(frame_bytes))
reply = client.get_data()

# Vehicle side server
server = netcom.ThreadedServer(host="0.0.0.0", port=5555)
server.listen()
server.send_data(frame_bytes, len(frame_bytes))
```

Both helpers wrap blocking sockets and expose `send_data`, `get_data`, and `close_client`/`listen` methods. `ThreadedServer.listen` accepts a single client and supports relaying CAN frames captured through `STN2120.read_can_bus` to the remote diagnostic endpoint.

## Packaging and installation

1. Ensure `setuptools` is available and update the package metadata in `setup.py` if required.
2. Build distributables:
   ```bash
   python setup.py sdist bdist_wheel
   ```
3. Install the package locally (using the freshly built artifacts or directly from source):
   ```bash
   pip install dist/stn2120-pck-0.0.1-py3-none-any.whl
   # or
   pip install .
   ```

During installation `pip` will pull in `pyserial` and other declared dependencies. The package targets Python 3.6+ as declared in `setup.py` and should run on Windows, Linux, or macOS where the STN2120 USB/UART drivers are available.

## Hardware and protocol compatibility

`ic_config.STN2120` supports the adapter roles `"clt_diag"` and `"clt_car"`, configuring paired serial ports for read/write streams and enabling CAN monitoring by default. The driver attempts the following OBD-II/SAE protocol identifiers, covering common CAN and legacy buses supported by STN2120 hardware: `31`, `8`, `1`, `7`, `9`, `2`, `3`, `4`, `5`, and `A` (SAE J1939). These values map to ISO 15765-4 (11-bit/29-bit at 500/250 kbit/s), SAE J1850 PWM/VPW, ISO 9141-2, ISO 14230-4 variants, and SAE J1939.

Successful communication requires a dual-UART STN2120 board wired to both the diagnostic tool and vehicle CAN bus, appropriate termination (especially for ISO 15765-4), and firmware that accepts the ST command set catalogued in `commands.py`.
