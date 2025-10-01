
from datetime import datetime
import socket
import threading
import re
from queue import Queue


import logging
logger = logging.getLogger(__name__)

HOST_NAME = socket.gethostname()  #'10.117.246.138'
HOST      = socket.gethostbyname(HOST_NAME)
PORT      = 5555

class socket_clients():
    """
    """

    def __init__(self, connection_data):
        """
        """
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.client.connect('192.168.1.82', PORT)
        self.client.connect(connection_data)
        logger.info("==socket_client, connected==" )
        self.client.send(b'server socket connected')
        print("initialization done")


    def send_data(self, data, frame_length):
        """
        """
        #cmd += b"\r\n" # terminate
        #logger.info("==  socket_client, client %s:%s ======" % (self.client.getpeername(),self.client.getsockname()) )
        ###---->self.client.send(data)
        logger.debug("socket_client.send_data:" + str(data))
        if data:
            size_sent = 0
            while size_sent < frame_length:
                tmp_sent = self.client.send(data)
                size_sent += tmp_sent
                if size_sent == 0:
                    logger.debug("Error: socket_client Sent frame size 0")
                    break
                #size_sent += tmp_sent





    def get_data(self):
        """   """
        try:
            data = self.client.recv(1024)
            return data
        except:
            logger.debug("socket_client.GET_DATA: NO DATA")
        #return  self.client.recv(1024)


    def close_client(self):
        """ """
        self.client.close()



class ThreadedServer(object):
    """
      from stn2120.network import netcom
      srv = netcom.ThreadedServer('192.168.1.82', 5555)
      srv.listen()

    """
    def __init__(self, host=None, port=None):
        if host:
            self.host = host
            self.port = port
        else:
            self.host = HOST
            self.port = PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        ####
        self.client = None
        self.address = None
        ####
        self.clients = {}


    def listen(self):
        """
        """
        self.sock.listen(5)
        self.client, self.address = self.sock.accept()
        print ("address", self.address)
        self.client.settimeout(600)
        self.client.send(b'server thread connected')



    def send_data(self, msj, frame_length):
        #if msj:
        #    #print(str(datetime.now().time())," ", msj)
        #    self.client.send(msj)

        if msj:
            size_sent = 0
            while size_sent < frame_length:
                tmp_sent = self.client.send(msj)
                size_sent += tmp_sent
                if size_sent == 0:
                    logger.debug("Error: ThreadedServer Sent frame size 0")
                    break





    def get_data(self):
        try:
            data = self.client.recv(1024)
            return data
        except:
            logger.debug("ThreadedServer.GET_DATA: NO DATA")




    def listenToClient(self, client, address):
        """         """
        ###->regex_role = '^(role=){1}(.*)$'
        # b'frame:412 10 00 00 06 00 FF 00 00 \r\n'
        ###->regex_frame = '^(frame:){1}([A-F0-9]{3}){1}(.*)$'
        #regex_frame = '^(frame:){1}([A-F0-9]{3}){1}(.*)\\r\\n$'
        size = 100
        while True:
            try:
                data_in = client.recv(size)
                #if data_in:
                #    data_in =
                ###->data = client.recv(size)
                ###->print("sF0:",data)
                ###->if data:
                ###->    data_frame = re.match(regex_frame, data.decode())
                ###->    if data_frame:
                ###->        #print("DATA:",data, " decode", data.decode() )
                ###->        print ("sF-->",data)
                ###->        self.clients['clt_diag'].send(data)
                ###->        continue
                ###->    #print ("server get data ", data)
                ###->    data_str = re.match(regex_role, data.decode())
                ###->    #print ("server get data ", data_str)

                ###->    if data_str:
                ###->        self.clients[data_str.group(2)] = client
                ###->        data2client = data_str.group(2)
                ###->        client.send(data2client.encode())

                ###->    if data == b'Get clients dict':
                ###->        client.send(str(list(self.clients)).encode())
                ###->else:
                ###->    raise error('Client disconnected')
            except:
                client.close()
                return False
