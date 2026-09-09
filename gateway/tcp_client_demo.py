import sys
import socket
import gateway.codec as codec
import gateway.message_pb2 as message_pb2

def read_reply(sock):
    incoming_msg = codec.read_message(sock)
    if incoming_msg is None:
        print("server closed")
        return None 

    msg_type, payload = incoming_msg

    if msg_type == message_pb2.ORDER_ACCEPT:
        msg = message_pb2.OrderAccept()
        msg.ParseFromString(payload)
        print(f"ACCEPT order_id={msg.order_id}")
    elif msg_type == message_pb2.ORDER_REJECT:
        msg = message_pb2.OrderReject()
        msg.ParseFromString(payload)
        print(f"REJECTED order_id={msg.order_id} because {msg.reason}")
    elif msg_type == message_pb2.TRADES:
        msg = message_pb2.Trades()
        msg.ParseFromString(payload)

        for t in msg.trades:
            print(
                f"TRADE bid={t.bid_order_id} ask={t.ask_order_id} "
                f"price={t.price} qty={t.quantity}"
            )
    else:
        print(f"unknow message type {msg_type}")
    return msg_type

        
def main():
    if len(sys.argv) != 2:
        print("usage python3 tcp_client.py <port>")
        sys.exit(1)
    port = int(sys.argv[1])

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect(("127.0.0.1", port))
        print(f"connected to server on port {port}")

        #1 adda resting sell 
        add_sell = message_pb2.AddOrder(
            client_order_id = 1,
            side = message_pb2.SELL,
            order_type = message_pb2.GTC,
            price = 100,
            quantity = 5,
        )

        codec.send_message(sock, message_pb2.ADD_ORDER, add_sell)
        read_reply(sock) #expect accept 

        #2 add a buy that matches
        add_buy = message_pb2.AddOrder(
            client_order_id = 2,
            side = message_pb2.BUY,
            order_type = message_pb2.GTC,
            price = 100,
            quantity = 5,
        )

        codec.send_message(sock, message_pb2.ADD_ORDER, add_buy)
        read_reply(sock) # get accept
        read_reply(sock) # get trades

    finally:
        sock.close()
        print("disconnected")

if __name__ == "__main__":
    main()