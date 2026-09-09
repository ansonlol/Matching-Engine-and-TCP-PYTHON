# Title
# Python Matching Engine & Multi-Client TCP Gateway
A object-oriented limit order book with a TCP + Protobuf order-entry gateway. Multiple clients can submit orders over the network; a single matcher thread applies them to a shared book through an application service layer.

This project models exchange-style architecture (gateway → service → engine). It is not a production HFT system.

## Features

- Order types: GTC, FAK, FOK, Market, GFD
- Price–time priority matching
- Add, cancel, and modify
- Book depth snapshot (`get_order_infos`)
- TCP order entry with length-prefixed Protobuf framing
- Multi-client support via inbound/outbound queues and one matcher thread
- Application layer: `OrderService` + `CancelFairy` (GFD / session-style cancels)

## Architecture

Client(s)
    │  TCP + Protobuf (framed)
    ▼
Gateway (tcp_server)
    │  Command queue
    ▼
Matcher  ──only writer──►  OrderService  ──►  OrderBook
    │                           │
    │                           └── CancelFairy (GFD)
    ▼
Reply queue ──► Gateway writer ──► Client(s)

engine/ — matching core (OrderBook, Order, Trade, levels, types)
services/ — OrderService (facade), CancelFairy (GFD policy outside the book)
gateway/ — codec, Protobuf, commands, matcher, TCP server, smoke client

Clients never touch the book directly. Only the matcher thread calls OrderService.

# Project layout
engine/          Order book and domain types
services/        OrderService, CancelFairy
gateway/         TCP server, matcher, codec, message.proto
tests/           Unit and multi-client integration tests
documents/       Notes and reference material

# Requirements

Python 3.10+ (3.11+ recommended)
protobuf (runtime + protoc to regenerate stubs)
sortedcontainers

# Example:
pip install protobuf sortedcontainers
Run all commands from the project root.
export PYTHONPATH=.

Generate Protobuf (when .proto changes)
cd gateway
protoc --python_out=. message.proto
cd ..

Start the server
python -m gateway.tcp_server 9999

Smoke tests (single client, many scenarios)
other terminal; server must be running
python -m gateway.smoke_gateway 9999

Multi-client match test
server must be running on a fresh process for a clean book
python -m tests.test_multi 9999

Note: The server keeps one in-memory book for its lifetime. Restart the server before integration tests if previous runs left resting orders.

Protocol
Framing (network byte order):
text[4 bytes length][4 bytes message type][N bytes protobuf payload]
length covers the type field + payload (same convention as the project codec).

# Design decisions

Single matcher thread — the book has one writer; network threads only enqueue/dequeue
queue.Queue — practical MPSC handoff in Python; in C++ HFT this maps to SPSC/lock-free rings
GFD via CancelFairy — time/session policy stays outside the matching engine
FOK — full-fill check against opposite-side liquidity before any partial trades
Market — sweep available liquidity; residual does not rest (Option B)
Service facade — gateway talks to OrderService, not OrderBook, so policy and matching stay separable

# Testing

tests/test.py (or unit tests under tests/)Engine / service behavior without TCPgateway/smoke_gateway.
Single-client TCP: match, cancel, FOK reject, modifytests/test_multi.pyTwo TCP clients; cross-connection match
Prefer a restarted server before smoke and multi-client runs so results are deterministic.

# Limitations

Not latency-oriented HFT (Python, locks/queues, no kernel bypass)
No persistence, replication, or recovery
No authentication or per-client authorization
No full market-data bus (trades returned to the active client)
In-memory state only; process restart clears the book

# Future work

END_SESSION (or admin) message wired to OrderService.end_session()
Market-data broadcast to all subscribers
Stronger reject codes (duplicate id, FOK, unknown order, etc.)
Subprocess-started server inside integration tests
Optional per-connection order ownership checks