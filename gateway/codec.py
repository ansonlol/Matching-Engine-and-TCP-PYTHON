import struct 

def encode_message(message_type:int, protobuf_message) -> bytes:
    payload = protobuf_message.SerializeToString()
    header = struct.pack("!II", len(payload) + 4, message_type)
    return header + payload

def recvall(sock, n:int) -> bytes:
    data = b""
    # get exactly n bytes of data
    #tcp may send more or not enough bytes
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None 
        data += packet 
    return data 

def read_message(sock) -> tuple[int, bytes] | None:
    header_data = recvall(sock, 8)
    if header_data is None:
        return None 
    
    message_length, messsage_type = struct.unpack("!II", header_data)

    payload = recvall(sock, message_length - 4)
    if payload is None:
        return None 
    return (messsage_type, payload)

def send_message(sock, message_type, protobuf_message):
    sock.sendall(encode_message(message_type, protobuf_message))
