from engine.order import Order, OrderModify
from engine.trade import Trade, TradeInfo, Trades
from engine.levels import OrderbookLevelInfos, LevelInfo, LevelInfos, LevelData
from engine.ordertypes import OrderId, Price, Side, Quantity, OrderType
from sortedcontainers import SortedDict
from operator import neg 

class OrderBook:
    def __init__(self):
        self._orders: dict[OrderId, Order] = {}
        self._bids: SortedDict[Price, list[Order]] = SortedDict(neg)
        self._asks: SortedDict[Price, list[Order]] = SortedDict()

        # for fok order we need leveldata
        self._level_data: dict[Price, LevelData] = {}

    #private api
    #1 check if any matches in the orderbook
    def _can_match(self, side:Side, price:Price ) -> bool:
        if side == Side.BUY:
            if not self._asks:
                return False
            # peak item is a tuple (price, list[order])
            return price >= self._asks.peekitem(0)[0]
        elif side == Side.SELL:
            if not self._bids:
                return False
            return price <= self._bids.peekitem(0)[0]
        return False
    
    #2 loop if continuesely have match orders in the orderbook
    def _match_orders(self):
        trades : Trades = []

        while True:
            if not self._asks or not self._bids:
                break 

            best_bid, buy_orders = self._bids.peekitem(0)
            best_ask, ask_orders = self._asks.peekitem(0)

            if best_bid < best_ask:
                break

            while buy_orders and ask_orders:
                bid = buy_orders[0]
                ask = ask_orders[0]

                quantity: Quantity = min(bid.remaining_quantity, ask.remaining_quantity)
                bid.fill(quantity)
                ask.fill(quantity)

                self._on_order_matched(bid.price, quantity, bid.is_filled)
                self._on_order_matched(ask.price, quantity, ask.is_filled)

                # clear the data structure
                if bid.is_filled:
                    del self._orders[bid.order_id]
                    buy_orders.pop(0)

                if ask.is_filled:
                    del self._orders[ask.order_id]
                    ask_orders.pop(0)

                trades.append(Trade(
                    bid_trade=TradeInfo(order_id=bid.order_id, price=bid.price, quantity=quantity),
                    ask_trade=TradeInfo(order_id=ask.order_id, price=ask.price, quantity=quantity)
                ))

            # check the entire layer
            if not buy_orders:
                del self._bids[best_bid]
            if not ask_orders:
                del self._asks[best_ask]

        if self._bids:
            buy_orders = self._bids.peekitem(0)[1]
            if buy_orders[0].order_type == OrderType.FILL_AND_KILL:
                self.cancel_order(buy_orders[0].order_id)
        if self._asks:
            ask_orders = self._asks.peekitem(0)[1]
            if ask_orders[0].order_type == OrderType.FILL_AND_KILL:
                self.cancel_order(ask_orders[0].order_id)
        return trades

    #10 on order add, to handle on order actions, fok and others
    def _on_order_added(self, order):
        data = self._level_data.setdefault(order.price, LevelData())
        data.quantity += order.remaining_quantity
        data.count += 1

    #11 on order cancel
    def _on_order_cancelled(self, order):
        data = self._level_data[order.price]
        data.quantity -= order.remaining_quantity
        data.count -= 1
        if data.count == 0:
            del self._level_data[order.price]
    #12 onorermatch
    def _on_order_matched(self, price, qty, fully_filled: bool):
        data = self._level_data[price]
        data.quantity -= qty
        if fully_filled:
            data.count -= 1
        if data.count == 0:
            del self._level_data[price]

    #13 can fully filled, for fok 
    def _can_fully_fill(self, price:Price, quantity:Quantity, side:Side) -> bool:
        if not self._can_match(side, price):
            return False 

        if side == Side.BUY:

            for ask_price in self._asks:
                if ask_price > price:
                    break
                level_quantity = self._level_data.get(ask_price, LevelData()).quantity 
                if level_quantity >= quantity:
                    return True 
                quantity -= level_quantity

        else:

            for bid_price in self._bids:
                if bid_price < price:
                    break 
                level_quantity = self._level_data.get(bid_price, LevelData()).quantity
                if level_quantity >= quantity:
                    return True 
                quantity -= level_quantity

        return False

    # public api
    #3 add order
    def add_order(self, order:Order) -> Trades:
        if order.order_id in self._orders:
            return []

        # handle the market order remvoe the residual
        is_market = order.order_type == OrderType.MARKET

        if is_market:
            if order.side == Side.BUY:
                if not self._asks:
                    return []
                # use the worst rpice
                order.to_good_till_cancel(self._asks.peekitem(-1)[0])
            else:
                if not self._bids:
                    return []
                order.to_good_till_cancel(self._bids.peekitem(-1)[0])

        if order.order_type == OrderType.FILL_OR_KILL and not self._can_fully_fill(order.price, order.initial_quantity, order.side):
            return []

        if order.order_type == OrderType.FILL_AND_KILL and not self._can_match(side=order.side, price=order.price):
            return []

        if order.side == Side.BUY:
            if order.price not in self._bids:
                self._bids[order.price] = []
            self._bids[order.price].append(order)

        elif order.side == Side.SELL:
            if order.price not in self._asks:
                self._asks[order.price] = []
            self._asks[order.price].append(order)

        self._orders[order.order_id] = order
        # add on order add
        self._on_order_added(order)

        # match first, if market is here still we remove that
        trades = self._match_orders()
        if is_market and order.order_id in self._orders: 
            self.cancel_order(order.order_id)

        return trades

    #4 cancel order
    def cancel_order(self, order_id:OrderId) -> None:
        if order_id not in self._orders:
            return 
        order = self._orders[order_id]
        del self._orders[order_id]

        if order.side == Side.BUY:
            self._bids[order.price].remove(order)
            if not self._bids[order.price]:
                del self._bids[order.price]
        elif order.side == Side.SELL:
            self._asks[order.price].remove(order)
            if not self._asks[order.price]:
                del self._asks[order.price]

        self._on_order_cancelled(order)

    # 5 modify order
    def modify_order(self, mod:OrderModify) -> Trades:
        if mod.order_id not in self._orders:
            return []
        order_type = self._orders[mod.order_id].order_type

        self.cancel_order(mod.order_id)
        return self.add_order(mod.to_order(order_type=order_type))

    # 6 size of orderbook memethod
    def size(self) -> int:
        return len(self._orders)

    #7 just dissemnate some info from orderbook
    def get_order_infos(self) -> OrderbookLevelInfos:
        bid_infos: LevelInfos = []
        ask_infos: LevelInfos = []

        for price, bid_orders in self._bids.items():
            level_quantity = 0
            for order in bid_orders:
                level_quantity += order.remaining_quantity
            bid_infos.append(LevelInfo(price=price, quantity=level_quantity))

        for price, ask_orders in self._asks.items():
            level_quantity = 0
            for order in ask_orders:
                level_quantity += order.remaining_quantity
            ask_infos.append(LevelInfo(price=price, quantity=level_quantity))

        return OrderbookLevelInfos(bids=bid_infos, asks=ask_infos)

    #8 helper functio for order service
    def has_order(self, order_id:OrderId):
        return order_id in self._orders

    #9 helper function for order service
    def get_order(self, order_id:OrderId):
        return self._orders.get(order_id)