import socket 
import gateway.codec as codec 
import risk_service.risk_message_pb2 as risk_message_pb2

class RiskClient():

    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, address, port):
        self.client_socket.connect((address, port))

    def close(self):
        self.client_socket.close()

    def order_check(self, order_id, account_id, symbol, side, quantity, price):
        req = risk_message_pb2.CheckOrder(
            order_id = order_id,
            account_id = account_id,
            symbol = symbol,
            side = side,
            quantity = quantity,
            price = price,
        )
        codec.send_message(self.client_socket, risk_message_pb2.RiskMessageType.CHECK_ORDER, req)

        incoming_message = codec.read_message(self.client_socket)
        if incoming_message is None:
            return False, "risk disconnected"

        msg_type, payload = incoming_message
        if msg_type != risk_message_pb2.RiskMessageType.RISK_DECISION:
            return False, f"unexpected type {msg_type}"

        decision = risk_message_pb2.RiskDecision()
        decision.ParseFromString(payload)
        return decision.allow, decision.reason

    def apply_fill(self, order_id, account_id, symbol, side, quantity):
        req = risk_message_pb2.ApplyFill(
            order_id = order_id,
            account_id = account_id,
            symbol = symbol,
            side = side,
            quantity = quantity,
        )
        codec.send_message(self.client_socket, risk_message_pb2.RiskMessageType.APPLY_FILL, req)

        incoming_message = codec.read_message(self.client_socket)
        if incoming_message is None:
            return False 

        msg_type, payload = incoming_message
        if msg_type != risk_message_pb2.RiskMessageType.APPLY_FILL_ACK:
            return False 

        reply = risk_message_pb2.ApplyFillAck()
        reply.ParseFromString(payload)
        return reply.ok