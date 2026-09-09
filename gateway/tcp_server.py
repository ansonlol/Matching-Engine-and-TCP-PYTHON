import sys
import gateway.codec as codec
import socket 
import queue
import threading

from gateway.matcher import Matcher
from gateway.commands import Command, Reply

def reader_loop(client_id:int, client_sock:socket.socket, in_q:queue.Queue, connections, lock) -> None:

    try:
        while True:
            incoming_message = codec.read_message(client_sock)
            if incoming_message is None:
                break
            msg_type, payload = incoming_message
            in_q.put(Command(client_id=client_id, message_type=msg_type, payload=payload))
    except OSError:
        pass 
    finally:
        try:
            client_sock.close()
        except OSError:
            pass
        with lock:
            connections.pop(client_id, None)

def writer_loop(out_q:queue.Queue, connections:dict[int, socket.socket], lock:threading.Lock) -> None:
    while True:
        reply: Reply = out_q.get()
        with lock:
            sock = connections.get(reply.client_id)
        if sock is None:
            continue 
        try:
            codec.send_message(sock, reply.message_type, reply.proto_msg)
        except OSError:
            with lock:
                connections.pop(reply.client_id, None)

def main():

    if len(sys.argv) != 2:
        print("usage python3 tcp_server.py <port>")
        sys.exit(1)
    port = int(sys.argv[1])

    # we use queue to store the orders
    in_q = queue.Queue()
    out_q = queue.Queue()

    #use matcher
    matcher = Matcher(in_q, out_q)
    matcher.start()

    # we creaet more than one connections, lets say multiple cllients
    connections: dict[int, socket.socket] = {}
    conn_lock = threading.Lock()
    next_id = 1

    # writer thread
    writer = threading.Thread(
        target = writer_loop,
        args=(out_q, connections, conn_lock),
        name="writer",
        daemon=True
    )
    writer.start()

    #create a tcp server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #reuse adress and start qukcly
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    #bind all interface
    server.bind(("0.0.0.0", port))

    #listen 
    server.listen(32)
    print(f"server listening on port {port}")

    try:
        while True:
            client_sock, client_addr = server.accept()
            #make the reading loop
            with conn_lock:
                client_id = next_id
                next_id += 1
                connections[client_id] = client_sock
            print(f"client {client_id} connected from {client_addr}")
            t = threading.Thread(
                target=reader_loop,
                args= (client_id, client_sock, in_q, connections, conn_lock),
                name=f"reader-{client_id}",
                daemon=True,
            )
            t.start()
        
    except KeyboardInterrupt:
        print("shutting down")
    finally:
        matcher.stop()
        server.close()

if __name__ == "__main__":
    main()