#!/usr/bin/python3

import socket
import threading

class ThreadedServer(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.clients = {}

    def listen(self):
        #print("ThreadedServer listening", self.sock)
        self.sock.listen()
        while True:
            client, address = self.sock.accept()
            print ("address", address)
            #self.clients[address] = client
            self.clients[client.getpeername()] = client
            client.settimeout(600)
            threading.Thread(target = self.listenToClient,args = (client,address)).start()

    def listenToClient(self, client, address):
        size = 1024
        while True:
            try:
                data = client.recv(size)
                if data:
                    # Set the response to echo back the recieved data
                    print ("server before send ", data)
                    response = data
                    #client.send(response)
                    if len(self.clients) == 2:
                        print ("client 2 client ready!! 123")
                        for c in self.clients:
                            #print ("client", client.getpeername())
                            #print (c)
                            if not c == client.getpeername():
                                print ("Sent to client:", c , " DATA:", response)
                                self.clients[c].send(response)
                                print("DATA SENT...")
                else:
                    raise error('Client disconnected')
            except:
                client.close()
                return False

if __name__ == "__main__":
    while True:
        #port_num = input("Port? ")
        port_num = 5555
        try:
            port_num = int(port_num)
            break
        except ValueError:
            pass

    tmp_ser = ThreadedServer('0.0.0.0',5555)
    tmp_ser.listen()
