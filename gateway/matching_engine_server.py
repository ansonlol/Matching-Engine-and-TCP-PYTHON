import sys 
import socket 

import gateway.codec as codec
import gateway.message_pb2 as message_pb2
from services.order_service import OrderService
from engine.order import Order, OrderModify
from engine.ordertypes import Side, OrderType

PROTO_SIDE = {
    message_pb2.BUY : Side.BUY,
    message_pb2.SELL : Side.SELL
}

PROTO_ORDER_TYPE = {
    message_pb2.GTC : OrderType.GOOD_TILL_CANCEL,
    message_pb2.FOK : OrderType.FILL_OR_KILL,
    message_pb2.FAK : OrderType.FILL_AND_KILL,
    message_pb2.MARKET : OrderType.MARKET,
    message_pb2.GFD : OrderType.GOOD_FOR_DAY,
}

def send_top_of_book(sock, service:OrderService):
    bp, bq, ap, aq = service.top_of_book()
    top = message_pb2.TopOfBook(
        bid_price = bp,
        bid_qty = bq,
        ask_price = ap,
        ask_qty = aq,
    )
    codec.send_message(sock, message_pb2.TOP_OF_BOOK, top)

def trades_to_proto(trades):
    pb_trades = []
    for t in trades:
        pb_trade = message_pb2.Trade(
            bid_order_id = t.bid_trade.order_id,
            ask_order_id = t.ask_trade.order_id,
            price = t.bid_trade.price,
            quantity = t.bid_trade.quantity
        )
        pb_trades.append(pb_trade)
    return message_pb2.Trades(trades=pb_trades)


def _handle_add(payload, sock, service:OrderService):
    msg = message_pb2.AddOrder()
    msg.ParseFromString(payload)

    try:
        order_type = PROTO_ORDER_TYPE[msg.order_type]
        side = PROTO_SIDE[msg.side]
    except KeyError:
        codec.send_message(sock, message_pb2.ORDER_REJECT, 
                           message_pb2.OrderReject(order_id=msg.client_order_id, reason="unknown side or type"))
        return 
    if order_type == OrderType.MARKET:
        order = Order.market(msg.client_order_id, side, msg.quantity)
    else:
        order = Order(order_type, msg.client_order_id, side, msg.price, msg.quantity)

    trades = service.add_order(order)

    if not trades and not service.has_order(msg.client_order_id):
        codec.send_message(sock, message_pb2.ORDER_REJECT, 
                                   message_pb2.OrderReject(order_id=msg.client_order_id, reason="no liquidity or rejected"))
        return 
    codec.send_message(sock, message_pb2.ORDER_ACCEPT,
                       message_pb2.OrderAccept(order_id=msg.client_order_id))

    if trades:
        codec.send_message(sock, message_pb2.TRADES, trades_to_proto(trades))
    send_top_of_book(sock, service)

def _handle_cancel(payload, sock, service:OrderService):
    msg = message_pb2.CancelOrder()
    msg.ParseFromString(payload)

    if not service.has_order(msg.order_id):
        codec.send_message(sock, message_pb2.ORDER_REJECT,
                            message_pb2.OrderReject(order_id=msg.order_id, reason="no such order id"))

        return 

    service.cancel_order(msg.order_id)

    codec.send_message(sock, message_pb2.ORDER_ACCEPT, 
                       message_pb2.OrderAccept(order_id=msg.order_id))
    send_top_of_book(sock, service)
    

def _handle_modify(payload, sock, service:OrderService):
    msg = message_pb2.ModifyOrder()
    msg.ParseFromString(payload)

    try:
        side = PROTO_SIDE[msg.side]
    except KeyError:
        codec.send_message(sock, message_pb2.ORDER_REJECT, 
                           message_pb2.OrderReject(order_id=msg.order_id, reason="bad side"))
        return 

    mod = OrderModify(msg.order_id, side, msg.price, msg.quantity)
    trades = service.modify_order(mod)

    if not trades and not service.has_order(msg.order_id):
        codec.send_message(sock, message_pb2.ORDER_REJECT, 
                           message_pb2.OrderReject(order_id=msg.order_id, reason="order rejected"))
        return 

    codec.send_message(sock, message_pb2.ORDER_ACCEPT, 
                       message_pb2.OrderAccept(order_id=msg.order_id))

    if trades:
        codec.send_message(sock, message_pb2.TRADES,
                           trades_to_proto(trades))
    send_top_of_book(sock, service)
        

def _dispatch(type, payload, sock, service):
    if type == message_pb2.ADD_ORDER:
        _handle_add(payload, sock, service)
    elif type == message_pb2.CANCEL_ORDER:
        _handle_cancel(payload, sock, service)
    elif type == message_pb2.MODIFY_ORDER:
        _handle_modify(payload, sock, service)
    else:
        codec.send_message(sock, message_pb2.ORDER_REJECT,
        message_pb2.OrderReject(order_id=0, reason="unknown type"))

def main():
    if len(sys.argv) != 2:
        print("python -m gateway.matching_engine_server 10000")
        sys.exit(1)
    port = int(sys.argv[1])

    engine_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    engine_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    engine_server.bind(("0.0.0.0", port))
    engine_server.listen(1)# 1 gateway 
    print(f"engine server listening on port {port}")

    order_service = OrderService()

    while True:
        gateway_sock, gateway_addr = engine_server.accept()
        print(f"{gateway_addr} connected")
        try:
            while True:
                
                incoming_message = codec.read_message(gateway_sock)
                if incoming_message is None:
                    break 
                message_type, payload = incoming_message
                _dispatch(message_type, payload, gateway_sock, order_service)

        finally:
            gateway_sock.close()

if __name__ == "__main__":
    main()