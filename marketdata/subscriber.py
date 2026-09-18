import socket 
import gateway.message_pb2 as message_pb2
from marketdata.md_server import MD_LAST_TRADE_SNAPSHOT
import gateway.codec as codec 
import marketdata.md_message_pb2 as md_pb2

sub = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sub.connect(("127.0.0.1", 10001))
print("subscribed")

while True:
    msg = codec.read_message(sub)
    if msg is None:
        break
    messgae_type, payload = msg 
    if messgae_type == message_pb2.TRADES:
        trades = message_pb2.Trades()
        trades.ParseFromString(payload)
        for x in trades.trades:
            print(f"TRADE price={x.price} qty={x.quantity}")

    elif messgae_type == MD_LAST_TRADE_SNAPSHOT:
        snap = md_pb2.LastTradeSnapshot()
        snap.ParseFromString(payload)
        print("Snapshot", snap.price, snap.quantity, snap.bid_order_id, "seq: ", snap.seq)

    elif messgae_type == message_pb2.TOP_OF_BOOK:
        top = message_pb2.TopOfBook()
        top.ParseFromString(payload)
        print("top: ", top.bid_price, top.bid_qty, top.ask_price, top.ask_qty)

