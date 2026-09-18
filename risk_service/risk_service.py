from engine.ordertypes import Side

class RiskService:

    def __init__(self, max_order_size:int=1000, max_position: int=5000):
        # account_id -> symbol -> signed position
        self._positions : dict[str, dict[str, int]] = {}
        self._max_position = max_position
        self._max_order_size = max_order_size

        

    def check_order(self, account_id:str, symbol:str, side, quantity, price) -> tuple[bool, str]:

        if price <= 0:
            return False, "invalid price"
        if quantity <=0:
            return False, "invalid quantity"
        if quantity > self._max_order_size:
            return False, "exceed max order size"

        if account_id not in self._positions:
            self._positions[account_id] = {}

        if symbol not in self._positions[account_id]:
            self._positions[account_id][symbol] = 0

        cur_pos = self._positions[account_id][symbol]

        if side == Side.BUY:
            projected = cur_pos + quantity
        else:
            projected = cur_pos - quantity

        if abs(projected) > self._max_position:
            return False, "exceed max position"

        return True, "ok"

    def apply_fill(self, account_id, symbol, side, quantity):

        if account_id not in self._positions:
            self._positions[account_id] = {}
        
        if symbol not in self._positions[account_id]:
            self._positions[account_id][symbol] = 0

        if side == Side.BUY:
            self._positions[account_id][symbol] += quantity 
        else:
            self._positions[account_id][symbol] -= quantity

    def get_position(self, account_id, symbol):
        return self._positions.get(account_id, {}).get(symbol, 0)