Libreria de python stn2120-pck
- inicializa STN2120
  -
  ```python
  stn2120.Board(portdev='/dev/ttyUSB0',baudrate=500000, protocol='31',role='clt_car')
  ```
  - role: la libreria admite 2 clases de clientes
    - clt_car: dispositivo que lee las tramas
    - clt_diag: dispositivo que recibe las tramas para insertarlas en bus de can
- permite enviar comandos AT:
  - send_cmd()
    ```python
    from stn2120 import stn2120
    t = stn2120.Board(portdev='/dev/ttyUSB0',baudrate=500000, protocol='31',role='clt_car')
    t.send_cmd()
    ```
- permite levantar TPC Server-Client
  - Este servidor habilita la comunicacion entre dos clientes
  ```python
  from stn2120.network import netcom
  srv = netcom.ThreadedServer('192.168.1.82', 5555)
  srv.listen()
  ```
- permite lectura y transmision entre 2 STN2120:
  - read_can_bus()
  ```python
  from stn2120 import stn2120
  q= stn2120.Board(portdev='/dev/ttyUSB0',baudrate=500000, protocol='31',role='clt_diag')
  q.read_can_bus()
  ```
