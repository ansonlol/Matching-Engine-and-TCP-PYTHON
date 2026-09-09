import sys
import socket
import gateway.codec as codec 
import gateway.message_pb2 as message_pb2 


def read_reply(sock):
    incoming_message = codec.read_message(sock)
    if incoming_message is None:
        print("server closed")
        return None
    message_type, payload = incoming_message

    if message_type == message_pb2.ORDER_ACCEPT:
        msg = message_pb2.OrderAccept()
        msg.ParseFromString(payload)
        print(f"order_id {msg.order_id} accepted, ")

    elif message_type == message_pb2.ORDER_REJECT:
        msg = message_pb2.OrderReject()
        msg.ParseFromString(payload)
        print(f"order_id {msg.order_id} rejected, reason {msg.reason}")

    elif message_type == message_pb2.TRADES:
        msg = message_pb2.Trades()
        msg.ParseFromString(payload)

        for t in msg.trades:
            print(
                f"Trade bid={t.bid_order_id} ask={t.ask_order_id}"
                f"price={t.price} qty={t.quantity}"
            )
    else:
        print("unknonw type")
    return message_type

# connect
def test_two_clients():

    if len(sys.argv) != 2:
        print("missing port")
        sys.exit(1)
    port = int(sys.argv[1])

    sock_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:

        sock_1.connect(("127.0.0.1", port))
        sock_2.connect(("127.0.0.1", port))

        # sock 1 is sell
        # sock 2 is buy

        add_sell = message_pb2.AddOrder(
            client_order_id = 1,
            side = message_pb2.SELL,
            order_type = message_pb2.GTC,
            price = 100,
            quantity = 5,
        )

        codec.send_message(sock_1, message_pb2.ADD_ORDER, add_sell)
        read_reply(sock_1)

        add_buy = message_pb2.AddOrder(
            client_order_id = 2,
            side = message_pb2.BUY,
            order_type = message_pb2.GTC,
            price = 100,
            quantity = 4,
        )

        codec.send_message(sock_2, message_pb2.ADD_ORDER, add_buy)
        t1=read_reply(sock_2)
        t2=read_reply(sock_2)

        assert t1 == message_pb2.ORDER_ACCEPT
        assert t2 == message_pb2.TRADES

    finally:
        sock_2.close()
        sock_1.close()

test_two_clients()