from engine.orderbook import OrderBook
from services.cancel_fairy import CancelFairy
from engine.ordertypes import OrderType, OrderId
from engine.order import Order, OrderModify
from engine.trade import Trades

class OrderService:
    def __init__(self, book:OrderBook | None = None):
        self._book = book if book is not None else OrderBook()
        self._fairy = CancelFairy(self._book)

    def add_order(self, order:Order) -> Trades:
        trades = self._book.add_order(order)

        # handle gfd
        if order.order_type == OrderType.GOOD_FOR_DAY and self._is_open(order.order_id):
            self._fairy.watch(order)
        
        return trades 

    def cancel_order(self, order_id:OrderId):
        self._book.cancel_order(order_id)
        self._fairy.unwatch(order_id)

    def modify_order(self, mod:OrderModify) -> Trades:
        self._fairy.unwatch(order_id=mod.order_id)
        trades = self._book.modify_order(mod)

        if self._is_open(mod.order_id):
            order = self._book.get_order(mod.order_id)
            if order is not None:
                self._fairy.watch(order)
        return trades

    def end_session(self):
        self._fairy.end_of_day()

    def size(self):
        return self._book.size()    

    def has_order(self, order_id:OrderId) -> bool:
        return self._book.has_order(order_id)

    # private api
    def _is_open(self, order_id:OrderId):
        # OrderBook doesn't expose _orders; add a tiny public helper on the book:
        # def has_order(self, order_id: OrderId) -> bool:
        #     return order_id in self._orders
        return self._book.has_order(order_id)

    def top_of_book(self) -> tuple[int, int, int, int]:
        return self._book.top_of_book()