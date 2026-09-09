from dataclasses import dataclass
from engine.ordertypes import OrderId, Price, Quantity

@dataclass(slots=True)
class TradeInfo:
    order_id: OrderId
    price: Price
    quantity: Quantity

@dataclass(slots=True)
class Trade:
    bid_trade: TradeInfo
    ask_trade: TradeInfo

Trades = list[Trade]