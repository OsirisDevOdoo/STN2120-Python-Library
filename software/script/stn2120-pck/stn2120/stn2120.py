

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
    """
    """

    def __init__(self, portdev=None, baudrate=None, protocol=None, role=None, timeout=0.1):
        """
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
        """
        """
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
        """
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
        logger.debug("Starting  DIAGNOSIS stn2120 ...")
        self.device._diagnosis()



    def read_can_bus(self):
        """ """
        logger.info ("reading 2 can bus ...")
        message = self.device.read_can_bus()


    def write_can_bus(self):
        """ """
        logger.info ("writing 2 can bus ...")
        self.device.write_to_canbus()

    def read_n_write(self):
        """
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
        """
            Closes the connection, and clears supported_commands
        """

        self.supported_commands = set()

        if self.device is not None:
            logger.info("Closing connection")
            self.device.close()
            self.device = None


    def status(self):
        """ returns the OBD connection status """
        if self.device is None:
            return OBDStatus.NOT_CONNECTED
        else:
            return self.device.status()
