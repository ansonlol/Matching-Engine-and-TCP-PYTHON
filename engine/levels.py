from dataclasses import dataclass
from typing import TypeAlias
from engine.ordertypes import Quantity, Price

#4 define level info
@dataclass(slots=True)
class LevelInfo:
    price: Price
    quantity: Quantity 

LevelInfos: TypeAlias = list[LevelInfo]

#define orderlevelinfos
@dataclass
class OrderbookLevelInfos:
    bids : LevelInfos
    asks : LevelInfos

@dataclass
class LevelData:
    quantity : Quantity = 0
    count : int = 0