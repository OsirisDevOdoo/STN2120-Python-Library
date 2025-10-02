

import serial
import time
import logging


from  .ic_config   import STN2120
from .utils import scan_serial, OBDStatus


import os


logging.basicConfig(
                     filename='stn2120.log'
                    ,format='%(asctime)s %(levelname)-8s %(message)s'
                    #,datefmt='%H:%M:%S'
                    ,level=logging.DEBUG)
#                  level=os.environ.get("LOGLEVEL", "INFO")
logger = logging.getLogger(__name__)

class Board(object):
    """Interfaz de alto nivel para interactuar con una placa STN2120.

    Esta clase envuelve la configuración del puerto serie y la comunicación
    con el dispositivo STN2120, permitiendo enviar comandos AT/ST, leer y
    escribir en el bus CAN y ejecutar flujos de diagnóstico. Los métodos
    públicos están pensados para escenarios en los que el equipo puede actuar
    como cliente de diagnóstico (``clt_diag``) o como cliente que simula el
    vehículo (``clt_car``).
    """

    def __init__(self, portdev=None, baudrate=None, protocol=None, role=None, timeout=0.1):
        """Inicializa una conexión con la placa STN2120.

        Args:
            portdev (list[str] | None): Lista de dispositivos serie disponibles
                donde se intentará abrir la conexión (p. ej. ``['/dev/ttyUSB0']``).
                Si es ``None`` se realizará el escaneo automático.
            baudrate (int | None): Velocidad del puerto serie en baudios. Si es
                ``None`` se delega la selección al objeto :class:`STN2120`.
            protocol (str | None): Identificador del protocolo OBD-II (por
                ejemplo ``"31"``). Puede dejarse en ``None`` para usar el
                predeterminado del firmware.
            role (str): Rol que desempeñará la placa en la topología CAN.
                Debe ser ``'clt_diag'`` para un cliente de diagnóstico o
                ``'clt_car'`` para un emulador de ECU. Este parámetro es
                obligatorio y determina el comportamiento interno del
                dispositivo.
            timeout (float): Tiempo máximo de espera (en segundos) para las
                operaciones de lectura/escritura en el puerto serie.

        Raises:
            AttributeError: Si ``role`` no se especifica o no pertenece a los
                valores admitidos.

        Side Effects:
            - Establece el atributo ``self.device`` con una instancia conectada
              de :class:`STN2120` si la conexión se realiza con éxito.
            - Muestra un mensaje en consola y detiene la inicialización si
              ``portdev`` no es una lista.
        """
        self.device = None

        self.timeout = timeout
        self.__last_command = b""
        self.__frame_counts = {}
        self.role = role # 'clt_diag'   'clt_car'
        if role is None:
            raise AttributeError("Role error, options: clt_diag or clt_car")
        if not portdev is None:
            if not isinstance(portdev, list):
                print ("portdev must be list type: ['/dev/ttyUSB0',]")
                return

        self.__connect(portdev, baudrate, protocol)

        #self.send_cmd()

    def __connect(self, portdev, baudrate, protocol):
        """Establece la conexión física con la placa STN2120."""
        ### portdev = '/dev/ttyUSB0'
        ### baudrate = 2000000
        ### protocol = "31"
        self.device = STN2120(portdev, baudrate, protocol, self.role, self.timeout)
        print("self.device ports", self.status())
        if self.status() == 'STN2120 Not Connected':
            logger.warning("error connecting devices")
            self.device = None
            return

    def send_cmd(self, cmd=None, node=None):
        """Envía un comando AT/ST al dispositivo y muestra la respuesta.

        Args:
            cmd (str | None): Cadena con el comando AT/ST a ejecutar. Si es
                ``None`` se solicitará interactivamente al usuario en consola.
            node (str | None): Identificador del nodo CAN destino cuando el
                comando implique una transmisión direccionada. El valor por
                defecto ``None`` indica que se usará el nodo por omisión
                configurado en el dispositivo.

        Returns:
            None: Las respuestas decodificadas se imprimen en la salida
            estándar, pero no se devuelven al llamador.

        Side Effects:
            Actualiza ``self.__last_command`` con el último comando enviado e
            imprime el resultado en la salida estándar.
        """
        logger.info("======================= send_cmd =======================")

        #cmd = 'ATRV'  # <-----
        if cmd is None:
            while not cmd:
                cmd = input("Commando AT/ST: ")
                logger.info("--->1 AT/ST: %s  <----", cmd)
                #messages = self.device.send_and_parse( b"ATRV")
        elif cmd:
            messages = self.device.send_and_parse( cmd.encode('utf-8'))
            self.__last_command = 'ATL1'
                #logger.info("--->ATL1: %s  <----", type(messages))
                #logger.info("--->ATL1: %s  <----", messages)
                #self.socket_client(messages[0])
        else:
            logger.info("---> No Command <----")

        self.__last_command = 'ATL1'
        messages = self.device.send_and_parse( cmd.encode('utf-8'), node)
        print("Result: ", messages)

    def start_diagnosis(self):
        """Inicia la rutina de diagnóstico continuo del dispositivo.

        Side Effects:
            Cambia el modo de operación del STN2120 para ejecutar
            ``_diagnosis`` y escribe la acción en el log.
        """
        logger.debug("Starting  DIAGNOSIS stn2120 ...")
        self.device._diagnosis()



    def read_can_bus(self):
        """Lee tramas entrantes del bus CAN.

        Returns:
            None: La información leída se almacena temporalmente en el objeto
            ``STN2120``; este método no expone un valor de retorno.

        Side Effects:
            Registra en el log la operación de lectura y delega en
            :meth:`STN2120.read_can_bus` la obtención de las tramas.
        """
        logger.info ("reading 2 can bus ...")
        message = self.device.read_can_bus()


    def write_can_bus(self):
        """Envía tramas CAN almacenadas al bus.

        Returns:
            None: La lógica de escritura y su resultado se gestionan dentro de
            :meth:`STN2120.write_to_canbus`.

        Side Effects:
            Registra en el log la operación de escritura y delega la
            transmisión en el objeto ``STN2120``.
        """
        logger.info ("writing 2 can bus ...")
        self.device.write_to_canbus()

    def read_n_write(self):
        """Realiza un ciclo combinado de lectura y escritura sobre el bus CAN.

        Este método es útil para escenarios en los que es necesario reenviar
        o transformar tramas en tiempo real mientras se mantiene la conexión
        activa.

        Side Effects:
            Delegada en :meth:`STN2120.read_n_write`, puede generar tráfico en
            el bus CAN y producir registros en el log.
        """
        logger.info ("read_n_write  ...")
        self.device.read_n_write()




    def __load_commands(self):
        """
            Queries for available PIDs, sets their support status,
            and compiles a list of command objects.
        """
        pass



    def close(self):
        """Cierra la conexión con la placa y limpia comandos soportados."""

        self.supported_commands = set()

        if self.device is not None:
            logger.info("Closing connection")
            self.device.close()
            self.device = None


    def status(self):
        """Devuelve el estado de conexión actual del STN2120."""
        if self.device is None:
            return OBDStatus.NOT_CONNECTED
        else:
            return self.device.status()
