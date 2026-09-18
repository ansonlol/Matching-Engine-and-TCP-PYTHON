import sys
import socket
import gateway.codec as codec
import gateway.message_pb2 as message_pb2

def connect(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", port))
    return sock

def read_one(sock):
    incoming = codec.read_message(sock)
    if incoming is None:
        raise RuntimeError("server closed")
    msg_type, payload = incoming
    return msg_type, payload

def expect_accept(sock, order_id: int):
    msg_type, payload = read_one(sock)
    assert msg_type == message_pb2.ORDER_ACCEPT, msg_type
    msg = message_pb2.OrderAccept()
    msg.ParseFromString(payload)
    assert msg.order_id == order_id
    print(f"  OK ACCEPT {order_id}")

def expect_reject(sock):
    msg_type, payload = read_one(sock)
    assert msg_type == message_pb2.ORDER_REJECT, msg_type
    msg = message_pb2.OrderReject()
    msg.ParseFromString(payload)
    print(f"  OK REJECT reason={msg.reason}")

def expect_trades(sock, quantity: int):
    msg_type, payload = read_one(sock)
    assert msg_type == message_pb2.TRADES, msg_type
    msg = message_pb2.Trades()
    msg.ParseFromString(payload)
    total = sum(t.quantity for t in msg.trades)
    assert total == quantity, total
    print(f"  OK TRADES qty={total}")

def send_add(sock, oid, side, otype, price, qty):
    msg = message_pb2.AddOrder(
        client_order_id=oid,
        side=side,
        order_type=otype,
        price=price,
        quantity=qty,
    )
    codec.send_message(sock, message_pb2.ADD_ORDER, msg)

def send_cancel(sock, oid):
    msg = message_pb2.CancelOrder(order_id=oid)
    codec.send_message(sock, message_pb2.CANCEL_ORDER, msg)

def send_modify(sock, oid, side, price, qty):
    msg = message_pb2.ModifyOrder(
        order_id=oid, side=side, price=price, quantity=qty
    )
    codec.send_message(sock, message_pb2.MODIFY_ORDER, msg)

def test_risk_max_order(sock):
    print("test max order size ")
    send_add(sock, 10, message_pb2.BUY, message_pb2.GTC, 100, 99999)
    expect_reject(sock)

def test_match(sock):
    print("test_match")
    send_add(sock, 1, message_pb2.SELL, message_pb2.GTC, 100, 5)
    expect_accept(sock, 1)
    send_add(sock, 2, message_pb2.BUY, message_pb2.GTC, 100, 5)
    expect_accept(sock, 2)
    expect_trades(sock, 5)

def test_cancel(sock):
    print("test_cancel")
    send_add(sock, 3, message_pb2.BUY, message_pb2.GTC, 90, 5)
    expect_accept(sock, 3)
    send_cancel(sock, 3)
    expect_accept(sock, 3)

def test_fok_reject(sock):
    print("test_fok_reject")
    send_add(sock, 4, message_pb2.BUY, message_pb2.FOK, 100, 100)
    expect_reject(sock)

def test_bad_cancel(sock):
    print("test_bad_cancel")
    send_cancel(sock, 99999)
    expect_reject(sock)

def test_modify(sock):
    print("test_modify")
    send_add(sock, 5, message_pb2.BUY, message_pb2.GTC, 80, 5)
    expect_accept(sock, 5)
    send_modify(sock, 5, message_pb2.BUY, 85, 5)
    expect_accept(sock, 5)

def main():
    if len(sys.argv) != 2:
        print("usage: python smoke_gateway.py <port>")
        sys.exit(1)
    port = int(sys.argv[1])
    sock = connect(port)
    try:
        test_match(sock)
        test_cancel(sock)
        test_fok_reject(sock)
        test_bad_cancel(sock)
        test_modify(sock)
        test_risk_max_order(sock    )
        print("all gateway smokes passed")
    finally:
        sock.close()

if __name__ == "__main__":
    main()