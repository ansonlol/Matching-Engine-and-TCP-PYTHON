from enum import Enum, auto
from typing import TypeAlias

#1 define ordertype
class OrderType(Enum):
    GOOD_TILL_CANCEL = auto()   # GTC
    FILL_AND_KILL = auto()      # FAK
    FILL_OR_KILL = auto()       # FOK
    MARKET = auto()
    GOOD_FOR_DAY = auto()

#2 defind side
class Side(Enum):
    BUY= auto()    
    SELL = auto()

#3 define using
Price: TypeAlias = int
Quantity: TypeAlias = int
OrderId: TypeAlias = int 