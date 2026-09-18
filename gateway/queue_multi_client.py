from gateway.engine_client import EngineClient
import gateway.codec as codec
import gateway.message_pb2 as message_pb2
from gateway.commands import Command, Reply
from gateway.spsc_ring import SpscRing
from marketdata.md_client import MdClient
from risk_service.risk_client import RiskClient
import risk_service.risk_message_pb2 as risk_message_pb2

import queue
import socket

SIDE_TO_RISK = {
    message_pb2.BUY : risk_message_pb2.RiskSide.RISK_BUY,
    message_pb2.SELL : risk_message_pb2.RiskSide.RISK_SELL,
}

def reader_loop(client_id, client_sock, in_q:queue.Queue, connections, lock):
    try:
        while True:

            incoming_message = codec.read_message(client_sock)
            if incoming_message is None:
                break
            msg_type, payload = incoming_message
            in_q.put(Command(client_id, msg_type, payload))

    except OSError:
        pass 

    finally:

        try:
            client_sock.close()
        except OSError:
            pass
        with lock:
            connections.pop(client_id, None)

def writer_loop(out_q:SpscRing, connections, lock):

    while True:
        reply = out_q.get()
        if reply is None:
            continue 

        with lock:
            sock = connections.get(reply.client_id)
        if sock is None:
            continue    

        try:
            codec.send_framed(sock, reply.message_type, reply.payload)
        except OSError:
            with lock:
                connections.pop(reply.client_id, None)

def engine_worker(in_q, out_q:SpscRing, engine:EngineClient, md_client:MdClient, risk_client:RiskClient):
    while True:
        cmd = in_q.get()

        # check whther the order is valid or not 
        if cmd.message_type in (message_pb2.MODIFY_ORDER, message_pb2.ADD_ORDER):
            if cmd.message_type == message_pb2.MODIFY_ORDER:
                msg = message_pb2.ModifyOrder()
                msg.ParseFromString(cmd.payload)
                order_id, side, qty, price = msg.order_id, msg.side, msg.quantity, msg.price

            elif cmd.message_type == message_pb2.ADD_ORDER:
                msg = message_pb2.AddOrder()
                msg.ParseFromString(cmd.payload)
                order_id, side, qty, price = msg.client_order_id, msg.side, msg.quantity, msg.price

            allow, reason = risk_client.order_check(order_id, "default","tsla", SIDE_TO_RISK.get(side, 0), qty, price)

            if not allow:
                reject = message_pb2.OrderReject(order_id=order_id, reason=reason)
                payload = reject.SerializeToString()
                while not out_q.push(Reply(cmd.client_id, message_pb2.ORDER_REJECT, payload)):
                    pass
                continue

        engine.send_framed(cmd.message_type, cmd.payload)

        reply = engine.read_message()
        if reply is None:
            print("connection engine closed")
            continue 

        reply_message_type, reply_payload = reply 
        msg = Reply(cmd.client_id, reply_message_type, reply_payload)

        while not out_q.push(msg):
            pass

        if reply_message_type == message_pb2.ORDER_ACCEPT and cmd.message_type in (message_pb2.CANCEL_ORDER, message_pb2.ADD_ORDER, message_pb2.MODIFY_ORDER):
            engine.client_socket.settimeout(0.1)

            try:
                got_top = False 

                reply2 = engine.read_message()
                if reply2 is not None:
                    t2, p2 = reply2
                    msg = Reply(cmd.client_id, t2, p2)

                    if t2 == message_pb2.TRADES:            
                        while not out_q.push(msg):
                            pass
                        try:
                            md_client.send_framed(t2, p2)
                        except OSError:
                            print("md publish failed")

                        trades = message_pb2.Trades()
                        trades.ParseFromString(p2)
                        for t in trades.trades:
                            risk_client.apply_fill(
                                t.bid_order_id, "defualt", "tsla",
                                risk_message_pb2.RISK_BUY, t.quantity,
                            )
                            risk_client.apply_fill(
                                t.ask_order_id, "default", "tsla",
                                risk_message_pb2.RISK_SELL, t.quantity,
                            )

                    elif t2 == message_pb2.TOP_OF_BOOK:
                        try:
                            md_client.send_framed(t2, p2)
                        except:
                            print("publish failed")
                        got_top = True
                
                if not got_top:   
                    reply3 = engine.read_message()
                    if reply3 is not None:
                        t3, p3 = reply3
                        if t3 == message_pb2.TOP_OF_BOOK:
                            try:
                                md_client.send_framed(t3, p3)
                            except OSError:
                                print("md publish failed")

            except socket.timeout:
                pass 
            finally:
                engine.client_socket.settimeout(None)

