import sys
import socket 

import gateway.codec as codec

class EngineClient():

    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, host:str, port:int ):
    
        self.client_socket.connect((host, port))
        print("connected")

    def close(self):
        self.client_socket.close()

    def send_message(self, message_type:int, proto_msg):
        codec.send_message(self.client_socket, message_type, proto_msg)

    def read_message(self) -> tuple[int, bytes] | None:
        return codec.read_message(self.client_socket)

    def send_framed(self, message_type, payload):
        codec.send_framed(self.client_socket, message_type, payload)