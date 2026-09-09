from __future__ import annotations

import queue
import threading
import gateway.message_pb2 as message_pb2
from typing import Callable

from gateway.commands import Command, Reply
from engine.ordertypes import Side, OrderType
from services.order_service import OrderService
from engine.order import Order, OrderModify

# declare the map for proto
PROTO_SIDE = {
    message_pb2.BUY : Side.BUY,
    message_pb2.SELL : Side.SELL,
}

PROTO_ORDER_TYPE = {
    message_pb2.GTC : OrderType.GOOD_TILL_CANCEL,
    message_pb2.FOK : OrderType.FILL_OR_KILL,
    message_pb2.FAK : OrderType.FILL_AND_KILL,
    message_pb2.MARKET : OrderType.MARKET,
    message_pb2.GFD : OrderType.GOOD_FOR_DAY,
}

def trades_to_proto(trades) -> message_pb2.Trades:
    pb_trades = []
    for t in trades:
        pb_trade = message_pb2.Trade(
            bid_order_id = t.bid_trade.order_id,
            ask_order_id = t.ask_trade.order_id,
            price = t.bid_trade.price,
            quantity = t.bid_trade.quantity,
        )
        pb_trades.append(pb_trade)
    return message_pb2.Trades(trades=pb_trades)

class Matcher:
    # single consumer commands

    def __init__(
        self,
        in_queue: queue.Queue[Command],
        out_queue: queue.Queue[Reply],
        service: OrderService | None = None,
    ):
        self._in = in_queue
        self._out = out_queue
        self._service = service if service is not None else OrderService()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(target = self._run, name="matcher", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0):
        self._stop.set()
        try:
            self._in.put_nowait(Command(client_id=-1, message_type=-1, payload=b""))
        except queue.Full:
            pass 
        if self._thread:
            self._thread.join(timeout=timeout)

    def _emit(self, client_id: int, message_type: int, proto_msg) -> None:
        self._out.put(Reply(client_id, message_type, proto_msg))

    def _run(self) -> None:
        while not self._stop.is_set():
            cmd = self._in.get()
            if self._stop.is_set() or cmd.client_id < 0:
                break 
            try: 
                self._dispatch(cmd)
            except Exception as e:
                # prodiction log
                self._emit(cmd.client_id, message_pb2.ORDER_REJECT, message_pb2.OrderReject(order_id=0, reason=f"internal error {e}"))

    def _dispatch(self, cmd:Command):
        if cmd.message_type == message_pb2.ADD_ORDER:
            self._handle_add(cmd)
        elif cmd.message_type == message_pb2.CANCEL_ORDER:
            self._handle_cancel(cmd)
        elif cmd.message_type == message_pb2.MODIFY_ORDER:
            self._handle_modify(cmd)
        else:
            self._emit(cmd.client_id, message_pb2.ORDER_REJECT, message_pb2.OrderReject(order_id=0, reason="unknown type"))


    def _handle_add(self, cmd:Command):
        msg = message_pb2.AddOrder()
        msg.ParseFromString(cmd.payload)
        cid = cmd.client_id

        try:
            order_type = PROTO_ORDER_TYPE[msg.order_type]
            side = PROTO_SIDE[msg.side]
        except KeyError:
            self._emit(
                cid, 
                message_pb2.ORDER_REJECT,
                message_pb2.OrderReject(
                    order_id=msg.client_order_id, reason="bad side or type"
                ),
            )
            return 

        if order_type == OrderType.MARKET:
            order = Order.market(msg.client_order_id, side, msg.quantity)
        else:
            order = Order(order_type, msg.client_order_id, side, msg.price, msg.quantity)

        trades = self._service.add_order(order)

        if not trades and not self._service.has_order(msg.client_order_id):
            self._emit(cid, message_pb2.ORDER_REJECT, message_pb2.OrderReject(order_id=msg.client_order_id, reason="no liquidity or rejected"))
            return 
        self._emit(cid, message_pb2.ORDER_ACCEPT, message_pb2.OrderAccept(order_id=msg.client_order_id))

        if trades:
            self._emit(cid, message_pb2.TRADES, trades_to_proto(trades))

    def _handle_cancel(self, cmd:Command) -> None:
        msg = message_pb2.CancelOrder()
        msg.ParseFromString(cmd.payload)
        cid = cmd.client_id

        if not self._service.has_order(msg.order_id):
            self._emit(cid, message_pb2.ORDER_REJECT, message_pb2.OrderReject(order_id=msg.order_id, reason="unknown order"))
            return 
        self._service.cancel_order(msg.order_id)
        self._emit(cid, message_pb2.ORDER_ACCEPT, message_pb2.OrderAccept(order_id=msg.order_id))

    def _handle_modify(self, cmd:Command) -> None:
        msg = message_pb2.ModifyOrder()
        msg.ParseFromString(cmd.payload)
        cid = cmd.client_id

        if not self._service.has_order(msg.order_id):
            self._emit(cid, message_pb2.ORDER_REJECT, message_pb2.OrderReject(order_id=msg.order_id, reason="unknown order"))
            return 
        try:
            side = PROTO_SIDE[msg.side]
        except KeyError:
            self._emit(cid, message_pb2.ORDER_REJECT, message_pb2.OrderReject(order_id=msg.order_id, reason="bad side"))
            return 
        mod = OrderModify(msg.order_id, side, msg.price, msg.quantity)
        trades = self._service.modify_order(mod)

        if not trades and not self._service.has_order(msg.order_id):
            self._emit(cid, message_pb2.ORDER_REJECT, message_pb2.OrderReject(order_id=msg.order_id, reason="modify rejected"))
            return 

        self._emit(cid, message_pb2.ORDER_ACCEPT, message_pb2.OrderAccept(order_id=msg.order_id))
        if trades:
            self._emit(cid, message_pb2.TRADES, trades_to_proto(trades))


