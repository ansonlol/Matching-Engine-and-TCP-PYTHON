from engine.orderbook import OrderBook
from engine.ordertypes import OrderId, OrderType
from engine.order import Order

class CancelFairy:
    def __init__(self, book:OrderBook):
        self._book = book
        self._good_for_day_ids : set[OrderId] = set()

    def watch(self, order:Order):
        if order.order_type == OrderType.GOOD_FOR_DAY:
            self._good_for_day_ids.add(order.order_id)

    def unwatch(self, order_id:OrderId):
        self._good_for_day_ids.discard(order_id)

    def end_of_day(self):
        ids = list(self._good_for_day_ids)
        self._good_for_day_ids.clear()
        for order_id in ids:
            self._book.cancel_order(order_id)