import sys 
import socket 
import threading

import gateway.codec as codec
import gateway.message_pb2 as message_pb2
import marketdata.md_message_pb2 as md_pb2

MD_LAST_TRADE_SNAPSHOT = 100


def broadcast(message_type, payload, lock, subscribers, exclude_sock=None):
    with lock:
        copy = list(subscribers)

    dead = []
    for sock in copy:
        if sock is exclude_sock:
            continue
        try:
            codec.send_framed(sock, message_type, payload)
        except OSError:
            dead.append(sock)

    if dead:
        with lock:
            for sock in dead:
                if sock in subscribers:
                    subscribers.remove(sock)

def handle(client_socket, lock, subscribers, state):
    with lock:
        subscribers.append(client_socket)
        if state["last_top"] is not None:
            codec.send_message(client_socket, message_pb2.TOP_OF_BOOK, state["last_top"])

        if state["last_snap"] is not None:
            codec.send_message(client_socket, MD_LAST_TRADE_SNAPSHOT, state["last_snap"])   
                

    try:
        while True:
            incoming_msg = codec.read_message(client_socket)
            if incoming_msg is None:
                break 
            msg_type, payload = incoming_msg
            if msg_type == message_pb2.TRADES:

                # add snapshot
                trades = message_pb2.Trades()
                trades.ParseFromString(payload)
                if trades.trades:
                    t = trades.trades[-1]
                    with lock:
                        snap = md_pb2.LastTradeSnapshot(
                            bid_order_id = t.bid_order_id,
                            ask_order_id = t.ask_order_id,
                            price = t.price,
                            quantity = t.quantity,
                            seq = state["seq"]
                        )
                        state["last_snap"] = snap
                        state["seq"] += 1   

                broadcast(msg_type, payload, lock, subscribers, exclude_sock=client_socket)
            elif msg_type == message_pb2.TOP_OF_BOOK:
                top = message_pb2.TopOfBook()
                top.ParseFromString(payload)
                with lock:
                    state["last_top"] = top 
                broadcast(msg_type, payload, lock, subscribers, exclude_sock=client_socket)
                        
            
    finally:
        with lock:
            if client_socket in subscribers:
                subscribers.remove(client_socket)
        client_socket.close()
    

def main():

    if len(sys.argv) != 2:
        print("python -m marketdata.md_server <md_sever port 10001> ")
        sys.exit(1)

    md_port = int(sys.argv[1])
    subscribers = []
    sub_lock = threading.Lock()

    state = {"last_snap" : None,
             "seq" : 1,
             "last_top" : None}

    md_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    md_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    md_server.bind(("0.0.0.0", md_port))
    md_server.listen(32)
    print(f"listening on port {md_port}")

    while True:

        client_socket, client_addr = md_server.accept()
        print(f"{client_addr} is connected")

        threading.Thread(
            target = handle,
            args= (client_socket, sub_lock, subscribers, state),
            daemon=True,).start()

        
if __name__ == "__main__":
    main()