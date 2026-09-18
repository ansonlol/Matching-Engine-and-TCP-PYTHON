import socket 
import gateway.codec as codec 
import gateway.message_pb2 as message_pb2

s = socket.socket()
s.connect(("127.0.0.1", 10001))

trades = message_pb2.Trades(
    trades = [
        message_pb2.Trade(
            bid_order_id = 1, ask_order_id = 2, price =100, quantity = 5
        )
    ]
)

codec.send_message(s, message_pb2.TRADES, trades)
print("publhsed")
s.close()