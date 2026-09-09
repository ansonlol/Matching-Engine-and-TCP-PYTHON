from engine.ordertypes import OrderType, OrderId, Side, Price, Quantity
from dataclasses import dataclass, field

# make order object
@dataclass(slots=True)
class Order:
    order_type: OrderType 
    order_id: OrderId
    side: Side 
    price: Price 
    initial_quantity: Quantity
    remaining_quantity: Quantity = field(init=False)

    def __post_init__(self):
        self.remaining_quantity = self.initial_quantity

    @classmethod
    def market(cls, order_id:OrderId, side:Side, quantity:Quantity):
        return cls(
            order_type=OrderType.MARKET,
            order_id = order_id,
            side=side,
            price=0,
            initial_quantity=quantity,
        )

    #public api
    @property
    def filled_quantity(self) -> Quantity:
        return self.initial_quantity - self.remaining_quantity
    @property
    def is_filled(self) -> bool:
        return self.remaining_quantity == 0

    def fill(self, quantity:Quantity) -> None:
        if quantity > self.remaining_quantity:
            raise ValueError(f"orderid {self.order_id} does not have enough quantity")
        self.remaining_quantity -= quantity

    def to_good_till_cancel(self, price:Price):
        if self.order_type != OrderType.MARKET:
            raise ValueError("only market orders can be converted to GTC this way")
        self.price = price
        self.order_type = OrderType.GOOD_TILL_CANCEL

@dataclass(slots=True)
class OrderModify:
    order_id: OrderId
    side: Side
    price: Price
    quantity: Quantity

    def to_order(self, order_type:OrderType) -> Order:
        #create a new order with the same orderid but different fields
        return Order(order_type, self.order_id, self.side, self.price, self.quantity)
    


        
