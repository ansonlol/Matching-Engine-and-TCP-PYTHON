import sys
import socket 

from gateway.engine_client import EngineClient
from gateway.queue_multi_client import reader_loop, writer_loop, engine_worker
from gateway.spsc_ring import SpscRing
from marketdata.md_client import MdClient
from risk_service.risk_client import RiskClient

import queue
import threading

def main():
    if len(sys.argv) != 5:
        print("python -m gateway.gateway_server <client_port> <engine_port> <md_port> <risk_port>")
        print("9999 10000 10001 10002")
        sys.exit(1)

    client_port = int(sys.argv[1])
    engine_port = int(sys.argv[2])
    md_port = int(sys.argv[3])
    risk_port = int(sys.argv[4])

    engine = EngineClient()
    engine.connect("127.0.0.1", engine_port)

    md = MdClient()
    md.connect("127.0.0.1", md_port)

    risk = RiskClient()
    risk.connect("127.0.0.1", risk_port)

    # data structures to handle multi clients
    in_q = queue.Queue()
    out_q = SpscRing(1024)
    connections: dict[int, socket.socket] = {}
    conn_lock = threading.Lock()
    next_id = 1

    # start writer thread once only 
    writer = threading.Thread(
        target=writer_loop,
        args=(out_q, connections, conn_lock),
        name="writer",
        daemon=True
    )
    writer.start()

    worker = threading.Thread(
        target=engine_worker,
        args=(in_q, out_q, engine, md, risk),
        name="engine worker",
        daemon=True,
    )
    worker.start()
    # make server to listen from orders client traders
    gateway_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gateway_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    gateway_server.bind(("0.0.0.0", client_port))
    gateway_server.listen(32) # change later for multi clients 
    print(f"gateway listening on {client_port}, engine { engine_port}, md {md_port}, risk {risk_port}")

    try:
        while True:

            client_socket, client_addr = gateway_server.accept()
            print(f"client conneced on {client_addr}")

            with conn_lock:
                client_id = next_id
                next_id += 1
                connections[client_id] = client_socket
            print(f"client {client_id} connected" )

            reader = threading.Thread(
                target=reader_loop,
                args=(client_id, client_socket, in_q, connections, conn_lock),
                name=f"reader {client_id}",
                daemon=True,
            )
            reader.start()

    except KeyboardInterrupt:
        print("shut down gateway")        

    finally:
        engine.close()
        gateway_server.close()



if __name__ == "__main__":
    main()