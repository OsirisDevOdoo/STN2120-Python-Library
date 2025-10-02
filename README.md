# STN2120 Python Library

## Descripción general
Este repositorio recopila los componentes necesarios para automatizar pruebas y diagnósticos de redes CAN utilizando tarjetas basadas en el chip **STN2120**. Incluye el paquete Python que gestiona el dispositivo, utilidades de red para el intercambio de tramas y scripts de servidor TCP que permiten la cooperación entre clientes con roles diferenciados ("clt_car" y "clt_diag").

## Requisitos
Las dependencias principales se mantienen en [`software/script/requirements.txt`](software/script/requirements.txt):

- `pyserial`
- `stn2120-pck`

> Se recomienda trabajar en un entorno virtual de Python 3.9+ para aislar las dependencias del sistema operativo.

## Instalación y ejecución rápida
1. **Crear y activar entorno virtual**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Instalar dependencias**:
   ```bash
   pip install -r software/script/requirements.txt
   ```
3. **Configurar el servidor TCP** (si se requiere comunicación entre clientes):
   ```bash
   python software/script/tcp_socket/thread_server.py
   ```
4. **Inicializar un cliente STN2120**:
   ```python
   from stn2120.stn2120 import Board

   board = Board(portdev=['/dev/ttyUSB0', '/dev/ttyUSB1'], baudrate=2000000, protocol="31", role='clt_car')
   board.read_can_bus()
   ```
   Recuerde cerrar la sesión con `board.close()` cuando termine.

## Resumen de submódulos relevantes (`software/script/`)
| Ruta | Descripción |
| --- | --- |
| [`stn2120-pck`](software/script/stn2120-pck) | Paquete Python instalable que encapsula la comunicación con la tarjeta STN2120, utilidades de diagnóstico y protocolos. |
| [`stn2120-pck/stn2120/stn2120.py`](software/script/stn2120-pck/stn2120/stn2120.py) | Define la clase `Board`, responsable de abrir el puerto serie, enviar comandos AT/ST y coordinar operaciones de lectura/escritura sobre el bus CAN según el rol asignado. |
| [`stn2120-pck/stn2120/network/netcom.py`](software/script/stn2120-pck/stn2120/network/netcom.py) | Implementa clientes y servidores TCP reutilizables (`socket_clients`, `ThreadedServer`) para transportar tramas entre procesos o equipos. |
| [`tcp_socket/thread_server.py`](software/script/tcp_socket/thread_server.py) | Servidor TCP multihilo de referencia que reenvía paquetes entre pares conectados y sirve como núcleo de distribución entre “clt_car” y “clt_diag”. |

## Ejemplos de flujo de trabajo
### 1. Captura desde "clt_car" y reenvío a "clt_diag"
1. **Lanzar el servidor TCP** (una sola instancia):
   ```bash
   python software/script/tcp_socket/thread_server.py
   ```
2. **Cliente "clt_car"**: inicia la lectura del bus CAN y prepara la conexión de red.
   ```python
   from stn2120.stn2120 import Board
   from stn2120.network.netcom import socket_clients

   car_board = Board(portdev=['/dev/ttyUSB0', '/dev/ttyUSB1'], baudrate=2000000, protocol="31", role='clt_car')
   car_board.read_can_bus()  # habilita STMA y comienza a monitorear el bus en bucle

   car_socket = socket_clients(("192.168.0.10", 5555))
   ```
   A partir de aquí puede reutilizar la lógica de `ic_config.read_can_bus()` para extraer cada línea recibida (`self.__port['r'].readline()`) y, por cada trama válida, enviar los bytes a través de `car_socket.send_data(frame, len(frame))`.
3. **Cliente "clt_diag"**: escucha al servidor y replica las tramas en su propio bus o las procesa localmente.
   ```python
   from stn2120.stn2120 import Board
   from stn2120.network.netcom import socket_clients

   diag_board = Board(portdev=['/dev/ttyUSB2', '/dev/ttyUSB3'], baudrate=2000000, protocol="31", role='clt_diag')
   diag_socket = socket_clients(("192.168.0.10", 5555))

   while True:
       payload = diag_socket.get_data()
       if payload:
           # Adaptar la lógica de escritura según la estructura de la trama recibida
           diag_board.device.send_and_parse(payload, node='w')
   ```
   Si se requiere inyección directa, puede personalizar `write_to_canbus()` para consumir una cola de tramas producida por el socket.

### 2. Comunicación directa utilizando `ThreadedServer`
```python
from stn2120.network.netcom import ThreadedServer

srv = ThreadedServer(host="0.0.0.0", port=5555)
srv.listen()  # Acepta un cliente y mantiene la sesión para intercambio bidireccional

# Una vez aceptado el cliente principal, utilice srv.send_data(...) y srv.get_data()
# para retransmitir mensajes entre pares o automatizar pruebas.
```
El servidor incorporado en `netcom.py` ofrece utilidades adicionales (envío segmentado, manejo de colas) y puede sustituir al script genérico de `tcp_socket/thread_server.py` cuando se requiere mayor control de logging.

## Cooperación entre "clt_car" y "clt_diag"
- **Asignación de roles**: el constructor de `Board` exige el parámetro `role` (`'clt_car'` o `'clt_diag'`). Esto habilita comportamientos específicos y evita usos ambiguos del dispositivo.
- **Pares de puertos serie**: el paquete espera recibir dos puertos (`['/dev/ttyUSB0', '/dev/ttyUSB1']`) para separar lectura y escritura, como se observa en la inicialización de `STN2120`.
- **Canal de transporte**: ambos clientes pueden conectarse al mismo servidor TCP (ya sea `ThreadedServer` desde `netcom.py` o el script de `tcp_socket`). El servidor reenvía cada trama recibida al otro cliente conectado.
- **Secuencia típica**:
  1. `clt_car` activa la monitorización (`read_can_bus()`) y recolecta tramas.
  2. Cada trama se entrega al servidor TCP mediante `socket_clients.send_data()`.
  3. `clt_diag` recibe los datos (`socket_clients.get_data()`) y los procesa, almacenándolos o reinyectándolos con `write_to_canbus()`.
  4. Ambos clientes pueden consultar `Board.status()` para verificar la conexión.

## Solución de problemas (Troubleshooting)
- **"STN2120 Not Connected"**: verifique el listado de puertos serie disponibles (`scan_serial()` en `utils.py`) y confirme que `portdev` se pase como lista (`['/dev/ttyUSB0', '/dev/ttyUSB1']`).
- **Conexiones TCP bloqueadas**: asegúrese de que el puerto 5555 esté libre y que no existan firewalls bloqueando el tráfico. Ajuste el parámetro `host` al iniciar el servidor para que escuche en la interfaz correcta.
- **Sin datos CAN**: revise la configuración de protocolo (`protocol="31"` para ISO 15765-4 CAN) y la alimentación de la interfaz física.
- **Desincronización entre clientes**: cuando se utilice el script `thread_server.py`, confirme que exactamente dos clientes estén conectados; el reenvío sólo se activa cuando se detectan ambos peers.

## Documentación adicional
Cuando se generen guías o manuales específicos, se almacenarán en el directorio `docs/`. Asegúrese de consultar dicha carpeta para tutoriales ampliados, referencias de comandos y casos de uso detallados.

