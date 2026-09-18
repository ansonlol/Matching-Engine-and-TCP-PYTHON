import sys
import socket 

from risk_service.risk_service import RiskService
from engine.ordertypes import Side
import risk_service.risk_message_pb2 as risk_message_pb2
import gateway.codec as codec

PROTO_SIDE = {
    risk_message_pb2.RiskSide.RISK_BUY : Side.BUY,
    risk_message_pb2.RiskSide.RISK_SELL : Side.SELL,
}

def handle_messages(client_socket, risk_service:RiskService):
    try:
        while True:
            incoming_message = codec.read_message(client_socket)
            if incoming_message is None:
                break 
            message_type, payload = incoming_message

            if message_type == risk_message_pb2.RiskMessageType.CHECK_ORDER:

                check_order = risk_message_pb2.CheckOrder()
                check_order.ParseFromString(payload)

                side = PROTO_SIDE.get(check_order.side)
                if side is None:
                    decision = risk_message_pb2.RiskDecision(
                        allow = False, reason = "bad side", order_id=check_order.order_id
                    )
                    codec.send_message(client_socket, risk_message_pb2.RISK_DECISION, decision)
                    continue 

                valid, reason = risk_service.check_order(check_order.account_id or "default", check_order.symbol or "tsla", side, check_order.quantity, check_order.price)
                
                decision = risk_message_pb2.RiskDecision(
                    allow = valid, reason=reason if not valid else "ok", order_id = check_order.order_id,
                )
                codec.send_message(client_socket, risk_message_pb2.RISK_DECISION, decision)

            elif message_type == risk_message_pb2.APPLY_FILL:

                apply_fill = risk_message_pb2.ApplyFill()
                apply_fill.ParseFromString(payload)

                side = PROTO_SIDE.get(apply_fill.side)
                if side is None:
                    reply = risk_message_pb2.ApplyFillAck(
                        ok = False, reason="bad side"
                    )
                    codec.send_message(client_socket, risk_message_pb2.APPLY_FILL_ACK, reply)
                    continue 

                risk_service.apply_fill(
                    apply_fill.account_id or "default",
                    apply_fill.symbol or "tsla",
                    side, 
                    apply_fill.quantity)
                reply = risk_message_pb2.ApplyFillAck(
                    ok = True, reason = "ok"
                )
                codec.send_message(client_socket, risk_message_pb2.APPLY_FILL_ACK, reply)


    finally:
        client_socket.close()
def main():

    if len(sys.argv) != 2:
        print("python -m risk_service.risk_server <risk_port>")
        sys.exit(1)

    risk_port = int(sys.argv[1])

    #also create tcp for gateway to connct

    risk_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    risk_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    risk_server.bind(("0.0.0.0", risk_port))
    risk_server.listen(8)
    print(f"listening on {risk_port}")

    #use risk service
    risk_service = RiskService()

    while True:
        client_socket, client_addr = risk_server.accept()
        print(f"connected by {client_addr}")
        
        handle_messages(client_socket, risk_service)

if __name__ == "__main__":
    main()