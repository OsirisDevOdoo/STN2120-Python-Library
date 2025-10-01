########################################################################
#
#
########################################################################

import re
import serial
import time
import sys
import glob

import redis

from .protocols import *
from .utils import OBDStatus
from .network.netcom import socket_clients
from datetime import datetime
from  stn2120.frames import frames
from stn2120.network import netcom

from queue import Queue
from threading import Thread

###
###import socket
import logging
logger = logging.getLogger(__name__)

class STN2120:
    """
    """

    STN_PROMPT = b'>'

    _SUPPORTED_PROTOCOLS = {
        "1" : SAE_J1850_PWM,
        "2" : SAE_J1850_VPW,
        "3" : ISO_9141_2,
        "4" : ISO_14230_4_5baud,
        "5" : ISO_14230_4_fast,
        "31" : ISO_15765_4_11bit_500k, # CAN
        "7" : ISO_15765_4_29bit_500k, # CAN
        "8" : ISO_15765_4_11bit_250k, # CAN
        "9" : ISO_15765_4_29bit_250k, # CAN
        "A" : SAE_J1939,              # CAN
        #"B" : None, # user defined 1
        #"C" : None, # user defined 2
    }


    _TRY_PROTOCOL_ORDER = [
        "31", # ISO_15765_4_11bit_500k
        "8", # ISO_15765_4_11bit_250k
        "1", # SAE_J1850_PWM
        "7", # ISO_15765_4_29bit_500k
        "9", # ISO_15765_4_29bit_250k
        "2", # SAE_J1850_VPW
        "3", # ISO_9141_2
        "4", # ISO_14230_4_5baud
        "5", # ISO_14230_4_fast
        "A", # SAE_J1939
    ]

    _TRY_BAUDS = [ 2000000, 38400, 9600, 230400, 115200, 57600, 19200 ]

    def __init__(self, portdev, baudrate, protocol, role, timeout):
        """
        """

        self.__status   = OBDStatus.NOT_CONNECTED
        self.__protocol = UnknownProtocol([])
        self.__role = role
        self.__client = ''
        self.__cmd = None
        self.__port = {'r':None, 'w':None}

        if portdev is None or len(portdev) <2:
            logger.info("Scanning for ports ..")
            portdev = self.get_ports_path()
            logger.info("Ports available: " + str(portdev))
            print("ports:",portdev)
            if len(portdev) != 2:
                logger.warning("NO STN2120 found")
                return None


        # clt_car
        if role == 'clt_diag':
            #w_timeout = 1
            #timeout   = 1
            baudrate  = 2000000
        elif role == 'clt_car':
            #w_timeout = 1
            #timeout   = 1
            baudrate  = 2000000
        else:
            raise AttributeError("Role error, options: clt_diag or clt_car")
        w_timeout = 0.001
        timeout   = 0.1



        #logger.info("==========INIT : %s %s %s" % (portdev, baudrate, protocol))
        i=0
        for item in self.__port:
            print("----------> item:",item)
            self.__port[item] = serial.serial_for_url(portdev[i],baudrate, \
                                    parity   = serial.PARITY_NONE, \
                                    stopbits = 1, \
                                    bytesize = 8,
                                    #writeTimeout=w_timeout,
                                    timeout = timeout) # seconds
            self.__initialize_node(protocol,item) # self.__port[item]
            i += 1

        #self.__port{'read'} = serial.serial_for_url(portdev[0],baudrate, \
        #                            parity   = serial.PARITY_NONE, \
        #                            stopbits = 1, \
        #                            bytesize = 8,
        #                            writeTimeout=w_timeout,
        #                            timeout = timeout) # seconds
        #self.__port{'write'} = serial.serial_for_url(portdev[1],baudrate, \
        #                            parity   = serial.PARITY_NONE, \
        #                            stopbits = 1, \
        #                            bytesize = 8,
        #                            writeTimeout=w_timeout,
        #                            timeout = timeout) # seconds


        # ---------------------------- ATZ (reset) ----------------------------
    def __initialize_node(self,protocol=None, node=None):
        try:
            self.__send(b"ATZ", node, 1 ) # wait 1 second for ELM to initialize
            # return data can be junk, so don't bother checking
        except serial.SerialException as e:
            self.__error(e)
            return
        # -------------------------- ATE0 (echo OFF) --------------------------

        r = self.__send(b"ATE0", node, 0.1)   #
        if not self.__isok(r, expectEcho=True):
            self.__error("ATE0 did not return 'OK'")
            return
        else:
            print (r)
        # ------------------------- ATH1 (headers ON) -------------------------
        r = self.__send(b"ATH1", node, 0.1 )
        if not self.__isok(r):
            self.__error("ATH1 did not return 'OK', or echoing is still ON")
            return

        # ------------------------ ATL1 (linefeeds OFF) -----------------------
        r = self.__send(b"ATL1", node, 0.1)  #<-------
        if not self.__isok(r):
            self.__error("ATL1 did not return 'OK'")
            return

        # by now, we've successfuly communicated with the ELM, but not the car
        self.__status = OBDStatus.STN_CONNECTED
        # try to communicate with the car, and load the correct protocol parser
        logger.info("======================= Protocol %s =======================", protocol)
        if self.set_protocol(protocol, node):
            self.__status = OBDStatus.CAR_CONNECTED
            logger.info("Connected Successfully:  BAUD=%s PROTOCOL=%s" %
                        (
                            self.__port[node].baudrate,
                            self.__protocol.ELM_ID,)
                       )
        else:
            logger.error("Connected to the adapter, but failed to connect to the vehicle")

        r = self.__send(b"STPO", node, 0.1)  #<-------
        if not self.__isok(r):
            self.__error("STPO did not return 'OK'")
            return
        try:
            ########## IMPORTANT ##########################################3
            ### Set CAN monitoring mode
            ###    Mode  Description
            ###     0    Receive only – no CAN ACKs (default)
            ###     1    Normal node – with CAN ACKs
            ###     2    Receive all frames, including frames with errors – no CAN ACKs.
            ###-------------- IMPORTAN!! --------------###
            ###  To read the CAN BUS it needs to be set on mode 1
            print(self.__send(b"STCMM 1", node, 0.1))#
            # return data can be junk, so don't bother checking
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
        #    ####################################################################
        #    ### Mode    Description
        #    ### 0       Adaptive timing off (fixed timeout)
        #    ### 1       Adaptive timing on, normal mode. This is the default option.
        #    ### 2       Adaptive timing on, aggressive mode.This option may increase throughput on
        #    ###         slower connections, at the expense of slightly increasing
        #    ###         the risk of missing frames.
            print(self.__send(b"ATAT 0",node, 0.1) )#
            # Set adaptive timing mode
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
            self.__send(b"ATCAF0",node, 0.1)
            # Turn CAN Auto Formatting on or off
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
            self.__send(b"ATV0", node, 0.1) #
            ### Variable DLC (Data Length Code) on/off*
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
            self.__send(b"ATR0", node, 0.1)#
            #  Turn responses on or off
        except serial.SerialException as e:
            self.__error(e)
            return


    def __write_init (self):
        """
        """
        logger.info("====== Init to WRITE =======" )
        try:
            print(self.__send(b"ATAL",node, 0.1)) # wait 1 second for ELM to initialize
            # Allow long messages.
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
            print(self.__send(b"ATCAF0",node, 0.1))
            # Turn CAN Auto Formatting on or off
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
            print(self.__send(b"ATV0", node, 0.1)) #
            ### Variable DLC (Data Length Code) on/off*
        except serial.SerialException as e:
            self.__error(e)
            return

        ###    ########## IMPORTANT ##########################################3
        ###    ### Set CAN monitoring mode
        ###    ####
        ###    ###    Mode  Description
        ###    ###     0    Receive only – no CAN ACKs (default)
        ###    ###     1    Normal node – with CAN ACKs
        ###    ###     2    Receive all frames, including frames with errors – no CAN ACKs.
        #->try:
        #->    print(self.__send(b"STCMM 1", delay=1))#
        #->    # return data can be junk, so don't bother checking
        #->except serial.SerialException as e:
        #->    self.__error(e)
        #->    return
        try:
            print(self.__send(b"ATR1", node, 0.1))#
            #  Turn responses on or off
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
            print(self.__send(b"ATS0", node, 0.1) )#
            #  Turn printing of spaces in OBD responses on or off
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
        #    ####################################################################
        #    ### Mode    Description
        #    ### 0       Adaptive timing off (fixed timeout)
        #    ### 1       Adaptive timing on, normal mode. This is the default option.
        #    ### 2       Adaptive timing on, aggressive mode.This option may increase throughput on
        #    ###         slower connections, at the expense of slightly increasing
        #    ###         the risk of missing frames.
            print(self.__send(b"ATAT0",node, 0.1) )#
            # Set adaptive timing mode
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
            print(self.__send(b"STPTO 25",node, 0.1)) #
            #  Set OBD request timeout. Takes a decimal para-meter in milliseconds
            # (1 to 65535). Default is 200 ms.
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
            print(self.__send(b"STPTOT 1",node, 0.1)) #
            # Set message transmission timeout
            # (1 to 65535). Default is 200 ms.
        except serial.SerialException as e:
            self.__error(e)
            return
        try:
            print(self.__send(b"STPTRQ 0", node, 0.1)) #
            # Set the minimum time between the last response
            # and the next request
        except serial.SerialException as e:
            self.__error(e)
            return
        logger.info("====== Init 2 WRITE DONE =======" )


    def set_protocol(self, protocol, node=None):
        logger.info("protocol: %s " % protocol)
        if protocol is not None:
            # an explicit protocol was specified
            if protocol not in self._SUPPORTED_PROTOCOLS:

                logger.error("%s is not a valid protocol. Please use \"1\" through \"A\"")
                return False
            return self.manual_protocol(protocol, node)
        else:
            # auto detect the protocol
            ### NOT AVAILABLE FOR STN2120 (YET)
            return self.auto_protocol()


    def manual_protocol(self, protocol, node=None):
        r = self.__send(b"STP" + protocol.encode(), node, 0.1)
        if not self.__isok(r):
            self.__error("STP did not return 'OK'")
            return
        #r0100 = self.__send(b"0100")

        #if not self.__has_message(r0100, "UNABLE TO CONNECT"):
        #    # success, found the protocol
        #    self.__protocol = self._SUPPORTED_PROTOCOLS[protocol](r0100)
        #    return True

        return True #False

    def __isok(self, lines, expectEcho=False):
        if not lines:
            return False
        if expectEcho:
            # don't test for the echo itself
            # allow the adapter to already have echo disabled
            print("isOK:", lines)
            return self.__has_message(lines, 'OK')
        else:
            return len(lines) == 1 and lines[0] == 'OK'


    def __has_message(self, lines, text):
        for line in lines:
            if text in line:
                return True
        return False


    def __error(self, msg):
        """ handles fatal failures, print logger.info info and closes serial """
        self.close()
        logger.error(str(msg))

    def status(self):
        return self.__status

    def protocol_name(self):
        return self.__protocol.ELM_NAME


    def protocol_id(self):
        return self.__protocol.ELM_ID

    def close(self):
        """
            Resets the device, and sets all
            attributes to unconnected states.
        """

        self.__status   = OBDStatus.NOT_CONNECTED
        self.__protocol = None

        if self.__port is not None:
            logger.info("closing port")
            self.__write(b"ATZ")
            self.__port.close()
            self.__port = None




    def add_frame_queue(self, queue_frames, clt):
        """ """
        #q_frames = Queue()
        #tmp_q.put(in_frame)
        #regex_frame = '^(frame:){1}([A-F0-9]{3}){1}(.*)$'
        while True:
            #----
            #tmp_frame = self.__client.get_data()
            tmp_frame = clt.get_data()
            #data_frame = re.match(regex_frame, tmp_frame.decode())
            if tmp_frame:
                queue_frames.put(tmp_frame)



    def read_can_bus (self):
        """
        """

        node='r'
        cmd = b'STMA\r'

        if self.__port[node]:
            self.__port[node].flushInput() # dump everything in the input buffer
            self.__port[node].write(cmd)   # turn the string into bytes and write
            self.__port[node].flush()
        last_frame =''

        while True:
            data = self.__port[node].readline()
            if last_frame != data:
                if data ==b'BUFFER FULL\r\n':
                    self.__port[node].flushInput()
                    self.__port[node].write(cmd)
                    self.__port[node].flush()
                    continue
                print('frame:', data)


        ##   'clt_car'
        ########################################################################
        ########################################################################
        if self.__role == 'clt_car':
            srv =  netcom.ThreadedServer('192.168.1.82', 5555)
            print("Socket ready to connect and waiting for diagnosis client")
            srv.listen()

            while True:
                data = srv.get_data()
                if data:
                    print ("srv:", data)
                    if data == b'client connected':
                        print ('client connected OK')
                        break
            print("while DONE")

            if self.__port:
                cmd = b"STMA\r\n" # terminate  b"STMA\r\n"
                logger.info("write: " + repr(cmd))
                self.__port.flushInput() # dump everything in the input buffer
                self.__port.write(cmd)   # turn the string into bytes and write
                self.__port.flush()      # wait for the output buffer to finish transmitting
                #buffer = bytearray()
                last_frame =''

            while True:
                data = self.__port.readline()
                if last_frame == data:
                    pass
                else:
                    last_frame = data
                    # if nothing was recieved
                    if not data:
                        logger.warning("Failed to read port")
                        break
                    #data = str(datetime.now().time()) + "FRAME: " + data.decode()
                    #socket_client(data)
                    #print ("before frame:", data)
                    #print (str(datetime.now().time()), "clt_car:", data)
                    data = b'h:'+ data[:3] + b',d:' + data[4:]
                    print ("->", data)
                    srv.send_data(data)
        ########################################################################
        ########################################################################
        ###    'clt_diag'
        elif self.__role == 'clt_diag':
            print("Socket ready to connect and waiting for car client")
            ### READ data from server
            #regex_frame = '^(frame:){1}([A-F0-9]{3}){1}(.*)$'
            while True:
                try:
                    clt = netcom.socket_clients(connection_data=('192.168.1.82', 5555))
                    break
                except:
                    pass

            while True:
                data = clt.get_data()
                if data:
                    print("client:", data)
                    if data == b'server connected':
                        break
            print("clt_diag OK")


            #self.__write_init()


            q_frames = Queue()
            tmp_thread = Thread(target=self.add_frame_queue, args=(q_frames, clt )).start()
            data=''
            #self.__write_init()
            while True:
                if not q_frames.empty():
                    data = q_frames.get()
                    split_frames = data.split(b'\r\n')
                    if len(split_frames) > 2:
                        for f in split_frames:
                            if not f == b'':
                                print(f)
                                self.__write2_bus(f)
                    else:
                        #print(data[:3],data[4:])
                        print(data)
                        self.__write2_bus(data)
        ########################################################################
        ########################################################################

    def writeToBus_test(self, frames_written):
        """   """
        #t_iter = iter(range(0,len(frames),2))
        #self.__write_init()
        #t_start = datetime.now().time()
        #for n in range(100):

        for f in frames:
            print ("--->",f)
            #self.__write2_bus(frames[f], frames[(f+1)])
            self.__write2_bus(f)
            frames_written.append(f[:-3])
            time.sleep(1)
        #print("Start:", str(t_start)," END:", str(datetime.now().time()))



    def write_to_canbus(self):
        """
        tmp_thread = Thread(target=self.add_frame_queue, args=(q_frames, clt )).start()
        """
        write_thread = Thread(target=self.writeToBus_test).start()


    def __write2_bus(self,frame):  # (self,id_can,data_can)
        """
        #t1 = time.time()
        #data_can = data_can.strip()
        #id_can = b'STPX h:' + id_can + b', d:' + data_can +  b', t:1  \r\n'
        """
        frame_pattern = b'^h:[A-F0-9]{1,3},d:([A-F0-9]{2} ){1,8}'
        if re.fullmatch(frame_pattern, frame):
            id_can  = b'STPX ' + frame + b' , t:1 \r'  # , t:6
            #print ("WRITE --> STPX:",id_can )
            logger.debug("W2B. ")
            self.__port['w'].flushInput()   # dump everything in the input buffer
            self.__port['w'].write(id_can)  # turn the string into bytes and write
            #self.__port.flush()        # wait for the output buffer to finish transmitting
            # data = self.__port[node].read_until(b'\r\n')
            #_ = self.__port['w'].read_until(self.STN_PROMPT)
            for n in range(15):
                time.sleep(1/1000000)

            logger.debug("W2B DONE")
            #logger.debug("f res:" + str(_))
        else:
            logger.info("Frame dont write to BUS:" + str(frame))
        return


    def send_and_parse(self, cmd, node=None):
        """
            send() function used to service all OBDCommands
            Sends the given command string, and parses the
            response lines with the protocol object.
            An empty command string will re-trigger the previous command
            Returns a list of Message objects
        """
        if node is None:
            node='w'

        if self.__status == OBDStatus.NOT_CONNECTED:
            logger.info("cannot send_and_parse() when unconnected")
            return None

        logger.info("====== send_and_parse: -%s- =======" % self.__role)

        lines = self.__send(cmd,node)
        ###-->self.__client.send_data(lines[0])
        #print("RES:", lines)
        #######################################################################
        ############## Block added to test write 2 bus ########################
        ##self.__write_init()
        ##self.__write2_bus('frame')
        #######################################################################
        return lines


    def __send(self, cmd, node = None, delay=None):
        """
            unprotected send() function

            will __write() the given string, no questions asked.
            returns result of __read() (a list of line strings)
            after an optional delay.
        """

        self.__write(cmd, node)

        if delay is not None:
            logger.debug("wait: %d seconds" % delay)
            time.sleep(delay)

        return self.__read(node)

    def __write(self, cmd, node=None):
        """
            "low-level" function to write a string to the port
        """

        if self.__port[node]:
            # self.__port[item]
            cmd += b"\r\n" # terminate
            logger.debug("write: " + repr(cmd))
            self.__port[node].flushInput() # dump everything in the input buffer
            self.__port[node].write(cmd) # turn the string into bytes and write
            self.__port[node].flush() # wait for the output buffer to finish transmitting
        else:
            logger.info("cannot perform __write() when unconnected")


    def __read(self, node=None):
        """
            "low-level" read function

            accumulates characters until the prompt character is seen
            returns a list of [/r/n] delimited strings
        """
        if not  self.__port[node]:
            logger.info("cannot perform __read() when unconnected")
            return []

        buffer = bytearray()

        while True:
            # retrieve as much data as possible
            #data =  self.__port[node].read( self.__port[node].in_waiting or 1)
            data =   self.__port[node].readline()

            # if nothing was recieved
            if not data:
                logger.warning("Failed to read port")
                #break
            #else:
            #    print("->",data)
            buffer.extend(data)


            # end on chevron (ELM prompt character)
            if self.STN_PROMPT in buffer:
                break

        # log, and remove the "bytearray(   ...   )" part
        #logger.debug("read: " + repr(buffer)[10:-1])
        #logger.info("read: " + repr(buffer)[10:-1])

        # clean out any null characters
        buffer = re.sub(b"\x00", b"", buffer)

        # remove the prompt character
        if buffer.endswith(self.STN_PROMPT):
            buffer = buffer[:-1]

        # convert bytes into a standard string
        string = buffer.decode("utf-8", "ignore")

        # splits into lines while removing empty lines and trailing spaces
        lines = [ s.strip() for s in re.split("[\r\n]", string) if bool(s) ]

        return lines

    def read_2_file(self):
        """
        """
        last_cmd = self.__cmd

        self.__write(last_cmd)
        f = open ("serial_output.txt", "w")

        while True:
            # retrieve as much data as possible
            data = self.__port.readline()
            if data:
                f.write(data.decode())
            if not last_cmd == self.__cmd:
                #last_cmd = self.__cmd
                t1 = time.time()
                print ("COMMAD CHANGED ..... last_cmd:",last_cmd, " self.__cmd:",self.__cmd )
                while True:
                    #last_cmd = self.__cmd
                    self.__write(b'STI')
                    data = self.__port.readline()
                    if data == b'STN2120 v5.0.0\r\n':
                        break
                print ("---------->", last_cmd, "    ", (time.time() -t1))
                self.__write(self.__cmd)
                #print ("---------->", last_cmd)
                data = self.__port.readline()
                f.write(data.decode())
                self.__cmd = b'STMA'
                print("--------------------->", (time.time() -t1) )

    def read_frames_2_queue(self, queue_read):
        """ """

        node = 'r'
        cmd = b'STMA\r'


        if self.__port[node]:
            self.__port[node].flushInput() # dump everything in the input buffer
            self.__port[node].write(cmd)   # turn the string into bytes and write
            self.__port[node].flush()
        last_frame =''
        while True:
            data = self.__port[node].readline()
            if data:
                if last_frame != data:
                    last_frame = data
                    if data ==b'BUFFER FULL\r\n':
                        self.__port[node].flushInput()
                        self.__port[node].write(cmd)
                        self.__port[node].flush()
                        continue
                    queue_read.put_nowait(data)
                    #print(data)



    def read_n_write(self):
        """
        """

        queue_read = Queue()
        frames_written = []

        read_thread = Thread(target=self.read_frames_2_queue, args=(queue_read,)).start()

        while queue_read.empty():
            pass

        #self.write_to_canbus()
        write_thread = Thread(target=self.writeToBus_test, args=(frames_written,)).start()

        data1 = b''
        while True:
            data = queue_read.get()
            if data[-2:] == b'\r\n':
                if data1 :
                    data = data1 + data
                #print("read:",data1,data) if data1 else print("READ:",data)
                print("f-->",data)
                data1 = b''
            else:
                data1 = data

        return


    ############################################################################
    ############################################################################
    ############################################################################
    #                            DIAGNOSIS
    ############################################################################
    ############################################################################
    ############################################################################

    def connect_remote_nodes(self):
        """
        Function to raise Server-Client and starts Threads:
          process_read_from_server
        """
        if self.__role == 'clt_diag':

            srv_diag =  netcom.ThreadedServer('192.168.1.133', 5555)
            logger.debug("DIAGNOSIS Client ready and waiting from CAR ")
            srv_diag.listen()


            while True:
                #print ("while ...clt_diag")
                data = srv_diag.get_data()
                if data:
                    if data == b'server socket connected':
                        return srv_diag

        elif self.__role == 'clt_car':
            while True:
                try:
                    srv_car = netcom.socket_clients(connection_data=('192.168.1.133',5555) )
                    logger.debug("CAR client ready and waiting for DIAGNOSIS")
                    break
                except:
                    pass

            while True:
                #print ("while ...clt_car")
                data = srv_car.get_data()
                if data:
                    if data == b'server thread connected':
                        return srv_car


    def read_frames_from_bus(self,list_written_frames, srv, last_process_frame ,node):
        """ """
        if node is None:
            node = 'r'
        if self.__port[node]:
            self.__port[node].flushInput()
            self.__port[node].write(b"STMA\r\n")
            self.__port[node].flush()

            #last_frame = ''
            while True:
                data = self.__port[node].read_until(b'\r\n')
                if data:
                    #print("read_port ----------------------->",data,"  ",time.time())
                    logger.debug("frame_from_port ---------> " + str(data.decode()))

                    if last_process_frame.lrem(self.__role,0,data[:-2]) > 0:
                        logger.debug("read_frame omited")
                        continue
                    logger.debug("send_frame_2_server ---------> " + data[:-2].decode() )
                    srv.send_data(b'fr:' + data[:-2], len(data[:-2]))

    def write_frame_to_bus(self, data,list_written_frames,last_process_frame):
        """
        """
        _ = last_process_frame.lpush(self.__role, data)
        logger.debug("write_frame_to_bus lpush->" + str(_))
        #logger.debug("write_frame_to_bus no frame in QUEUE")
        self.__write2_bus(b'h:'+ data[:3] + b',d:' + data[4:])


    def process_read_from_server(self, list_written_frames, tmp_srv, last_process_frame ):
        """
        Thread that reads data FROM SERVER and place it into a Queue
        """
        print("process_read_from_server")
        while True:
            data = tmp_srv.get_data()
            if data:
                #print("data_from_server->",data)
                logger.debug("frame_from_server: " + data.decode() )
                if data.count(b'fr:') > 1:
                    split_data = data.split(b'fr:')
                    for d in split_data[1:]:
                        self.write_frame_to_bus(d,list_written_frames,last_process_frame)
                else:
                    self.write_frame_to_bus(data[3:],list_written_frames,last_process_frame)



    def _diagnosis(self):
        """
        """
        # QUEUEs to store data to read & write
        list_written_frames = []
        last_process_frame = redis.Redis(db=0)
        _ = last_process_frame.delete(self.__role)
        logger.debug("delete from REDIS " + self.__role + str(_))

        logger.debug("connecting remote nodes")
        srv =  self.connect_remote_nodes()
        if srv:
            print("Queues DONE")
        else:
            raise AttributeError("Nodes not connected ...")
        ########################################################################
        # Thread:  read FRAMES from bus and send through server
        #
        logger.debug(" starting Thread: read_frames_from_bus")
        thread_read_from_bus = Thread(target=self.read_frames_from_bus,
                               args=(list_written_frames, srv,
                                     last_process_frame , 'r'))
        thread_read_from_bus.start()
        logger.debug(" Thread read_frames_from_bus: started ")

        ########################################################################
        logger.debug(" starting Thread: process_read_from_server")
        thread_read_from_srv = Thread(target=self.process_read_from_server,
                                      args=(list_written_frames,
                                            srv,last_process_frame )).start()
        logger.debug(" thread process_read_from_server started")


        return



        ########################################################################
        ########################################################################
        ########################################################################


    def try_port(self, port_path):
        """    """
        try:
            s = serial.Serial(port_path)
            s.close()
            return True
        except serial.SerialException:
            pass
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise e
        return False


    def get_ports_path (self):
        """    """
        available    = []
        possible_ports = []

        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            possible_ports += glob.glob("/dev/rfcomm[0-9]*")
            possible_ports += glob.glob("/dev/ttyUSB[0-9]*")

        for port  in possible_ports:
            if self.try_port(port):
                available.append(port)

        return available
