import socket 
import gateway.codec as codec

class MdClient():

    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, host:str, port:int):
        self.client_socket.connect((host, port))
        print("connected")

    def close(self):
        self.client_socket.close()

    def send_framed(self, msg_type, payload):
        codec.send_framed(self.client_socket, msg_type, payload)

        