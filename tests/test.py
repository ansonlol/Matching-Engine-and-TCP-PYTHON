from engine.orderbook import OrderBook
from engine.order import Order, OrderModify
from engine.ordertypes import OrderType, Side
from services.order_service import OrderService

# ---------- helpers ----------

def gtc_buy(oid, price, qty):
    return Order(OrderType.GOOD_TILL_CANCEL, oid, Side.BUY, price, qty)

def gtc_sell(oid, price, qty):
    return Order(OrderType.GOOD_TILL_CANCEL, oid, Side.SELL, price, qty)

def gfd_buy(oid, price, qty):
    return Order(OrderType.GOOD_FOR_DAY, oid, Side.BUY, price, qty)

def gfd_sell(oid, price, qty):
    return Order(OrderType.GOOD_FOR_DAY, oid, Side.SELL, price, qty)

# ---------- OrderBook: basic ----------

def test_add_cancel():
    book = OrderBook()
    book.add_order(gtc_buy(1, 100, 5))
    assert book.size() == 1
    book.cancel_order(1)
    assert book.size() == 0
    print("test_add_cancel OK")

def test_match_partial():
    book = OrderBook()
    book.add_order(gtc_buy(1, 100, 10))
    trades = book.add_order(gtc_sell(2, 100, 4))
    assert len(trades) == 1
    assert trades[0].bid_trade.quantity == 4
    assert book.size() == 1
    assert book.get_order(1).remaining_quantity == 6
    print("test_match_partial OK")

def test_no_match_spread():
    book = OrderBook()
    book.add_order(gtc_buy(1, 100, 5))
    trades = book.add_order(gtc_sell(2, 105, 5))
    assert len(trades) == 0
    assert book.size() == 2
    print("test_no_match_spread OK")

def test_full_match_both_gone():
    book = OrderBook()
    book.add_order(gtc_buy(1, 100, 5))
    trades = book.add_order(gtc_sell(2, 100, 5))
    assert len(trades) == 1
    assert book.size() == 0
    print("test_full_match_both_gone OK")

def test_duplicate_id_rejected():
    book = OrderBook()
    book.add_order(gtc_buy(1, 100, 5))
    trades = book.add_order(gtc_buy(1, 101, 5))
    assert trades == []
    assert book.size() == 1
    print("test_duplicate_id_rejected OK")

# ---------- modify ----------

def test_modify_price():
    book = OrderBook()
    book.add_order(gtc_buy(1, 100, 5))
    trades = book.modify_order(OrderModify(1, Side.BUY, 105, 5))
    assert book.size() == 1
    o = book.get_order(1)
    assert o is not None and o.price == 105
    print("test_modify_price OK")

def test_modify_then_match():
    book = OrderBook()
    book.add_order(gtc_sell(1, 105, 5))
    book.add_order(gtc_buy(2, 100, 5))  # no match
    trades = book.modify_order(OrderModify(2, Side.BUY, 105, 5))
    assert len(trades) == 1
    assert book.size() == 0
    print("test_modify_then_match OK")

# ---------- FAK ----------

def test_fak_no_liquidity_rejected():
    book = OrderBook()
    trades = book.add_order(
        Order(OrderType.FILL_AND_KILL, 1, Side.BUY, 100, 5)
    )
    assert trades == []
    assert book.size() == 0
    print("test_fak_no_liquidity_rejected OK")

def test_fak_partial_rest_cancelled():
    book = OrderBook()
    book.add_order(gtc_sell(1, 100, 3))
    trades = book.add_order(
        Order(OrderType.FILL_AND_KILL, 2, Side.BUY, 100, 10)
    )
    assert len(trades) == 1
    assert trades[0].bid_trade.quantity == 3
    assert book.size() == 0  # FAK residual cancelled, sell fully filled
    print("test_fak_partial_rest_cancelled OK")

# ---------- FOK -------------

def test_fok_fully_filled():
    book = OrderBook()
    book.add_order(Order(OrderType.GOOD_TILL_CANCEL, 1, Side.SELL, 100, 5))
    trades = book.add_order(Order(OrderType.FILL_OR_KILL, 2, Side.BUY, 100, 5))
    assert len(trades) == 1
    assert book.size() == 0

    book.add_order(Order(OrderType.GOOD_TILL_CANCEL, 3, Side.SELL, 100, 10))
    trades = book.add_order(Order(OrderType.FILL_OR_KILL, 4, Side.BUY, 100, 5))
    assert len(trades) == 1
    assert book.size() == 1
    print("test_fok_fully_filled OK")

def test_fok_partial_filled():
    book = OrderBook()
    book.add_order(Order(OrderType.GOOD_TILL_CANCEL, 1, Side.SELL, 100, 3))
    trades = book.add_order(Order(OrderType.FILL_OR_KILL, 2, Side.BUY, 100, 5))
    assert trades == []
    assert book.size() == 1
    print("test_fok_partial_fill OK")

# ---------- Market ----------

def test_market_buy_sweeps_and_no_rest():
    book = OrderBook()
    book.add_order(gtc_sell(1, 100, 3))
    book.add_order(gtc_sell(2, 101, 3))
    trades = book.add_order(Order.market(3, Side.BUY, 5))
    assert sum(t.bid_trade.quantity for t in trades) == 5
    assert book.size() == 1  # 1 qty left on sell @ 101
    assert not book.has_order(3)  # market does not rest
    print("test_market_buy_sweeps_and_no_rest OK")

def test_market_no_liquidity():
    book = OrderBook()
    trades = book.add_order(Order.market(1, Side.BUY, 5))
    assert trades == []
    assert book.size() == 0
    print("test_market_no_liquidity OK")

# ---------- depth ----------

def test_get_order_infos():
    book = OrderBook()
    book.add_order(gtc_buy(1, 100, 5))
    book.add_order(gtc_buy(2, 100, 3))
    book.add_order(gtc_sell(3, 105, 4))
    infos = book.get_order_infos()
    assert len(infos.bids) == 1
    assert infos.bids[0].price == 100
    assert infos.bids[0].quantity == 8
    assert len(infos.asks) == 1
    assert infos.asks[0].quantity == 4
    print("test_get_order_infos OK")

# ---------- OrderService + GFD ----------

def test_service_gfd_end_session():
    svc = OrderService()
    svc.add_order(gfd_buy(1, 100, 5))
    svc.add_order(gfd_sell(2, 110, 5))
    assert svc.size() == 2
    svc.end_session()
    assert svc.size() == 0
    print("test_service_gfd_end_session OK")

def test_service_gfd_fully_filled_not_left():
    svc = OrderService()
    svc.add_order(gtc_sell(1, 100, 5))
    svc.add_order(gfd_buy(2, 100, 5))
    assert svc.size() == 0
    svc.end_session()  # must not crash
    assert svc.size() == 0
    print("test_service_gfd_fully_filled_not_left OK")

def test_service_cancel_unwatches():
    svc = OrderService()
    svc.add_order(gfd_buy(1, 100, 5))
    svc.cancel_order(1)
    assert svc.size() == 0
    svc.end_session()
    assert svc.size() == 0
    print("test_service_cancel_unwatches OK")

def test_service_modify_gfd_still_watched():
    svc = OrderService()
    svc.add_order(gfd_buy(1, 100, 5))
    svc.modify_order(OrderModify(1, Side.BUY, 99, 5))
    assert svc.size() == 1
    svc.end_session()
    assert svc.size() == 0
    print("test_service_modify_gfd_still_watched OK")

# ---------- runner ----------

if __name__ == "__main__":
    test_add_cancel()
    test_match_partial()
    test_no_match_spread()
    test_full_match_both_gone()
    test_duplicate_id_rejected()
    test_modify_price()
    test_modify_then_match()
    test_fak_no_liquidity_rejected()
    test_fak_partial_rest_cancelled()
    test_fok_fully_filled()
    test_fok_partial_filled()
    test_market_buy_sweeps_and_no_rest()
    test_market_no_liquidity()
    test_get_order_infos()
    test_service_gfd_end_session()
    test_service_gfd_fully_filled_not_left()
    test_service_cancel_unwatches()
    test_service_modify_gfd_still_watched()
    print("All tests passed")