Your old README still describes the **single-process matcher**. Here’s an updated version that matches what you built.

```markdown
# Python Matching Engine, Gateway, Market Data & Risk

A multi-process, exchange-style learning system: limit order book, TCP order-entry gateway, market-data fan-out, and a pre-trade risk service. Messages use length-prefixed Protobuf framing.

This is a teaching / Career Kickstarter–style project, **not** a production HFT stack.

## Architecture

```text
Traders (smoke / multi-client)
    │  TCP :9999  (ADD / CANCEL / MODIFY → ACCEPT / REJECT / TRADES)
    ▼
┌─────────────────────────────┐
│ Gateway                     │
│  readers → queue → worker   │
│  worker → writer (SPSC out) │
└───────┬───────────┬─────────┘
        │           │
        │ Risk      │ Engine
        │ :10002    │ :10000
        ▼           ▼
   Risk service   Matching engine
   (check/fill)   (OrderService → OrderBook)
        │
        │ on TRADES / TOP_OF_BOOK
        ▼
   Market data :10001  →  subscribers (snapshot + live)
```

| Process | Port (example) | Role |
|---------|----------------|------|
| Matching engine | 10000 | Only writer to the book |
| Market data | 10001 | Trade + top-of-book fan-out; late-join snapshot |
| Risk | 10002 | Pre-trade checks; apply fills |
| Gateway | 9999 | Client sessions; orchestrates risk → engine → MD |

Clients never touch the book. The gateway is the only process that dials engine, risk, and MD.

## Features

- Order types: GTC, FAK, FOK, Market, GFD  
- Price–time priority matching; add / cancel / modify  
- Multi-client gateway (thread-per-client readers, one engine worker)  
- Length-prefixed Protobuf framing (shared `codec`)  
- GFD via `CancelFairy` outside the book  
- Market data: live `TRADES`, `TOP_OF_BOOK`, last-trade snapshot + seq  
- Risk: max order size, max \|position\|, invalid price/qty (defaults: account `default`, symbol `tsla`)  
- Optional SPSC ring for worker → writer outbound path  

## Project layout

```text
engine/           OrderBook, Order, Trade, levels, types
services/         OrderService, CancelFairy
gateway/          gateway_server, engine client, codec, message.proto, queues/SPSC
marketdata/       md_server, md_client, subscriber, md_message.proto
risk_service/     risk_server, risk_client, risk_service, risk_message.proto
tests/            smoke_gateway, test_multi, unit tests
```

## Requirements

- Python 3.10+  
- `protobuf`, `sortedcontainers`  
- `protoc` matching your `protobuf` major version  

```bash
pip install protobuf sortedcontainers
export PYTHONPATH=.
```

### Regenerate stubs (when `.proto` changes)

```bash
cd gateway && protoc --python_out=. message.proto && cd ..
cd marketdata && protoc --python_out=. md_message.proto && cd ..
cd risk_service && protoc --python_out=. risk_message.proto && cd ..
```

Use **unique enum value names** across protos (e.g. `RISK_BUY` vs gateway `BUY`) to avoid descriptor-pool clashes.

## Running

From project root, **four servers** then clients:

```bash
# Terminal 1 – engine (restart for a clean book)
python -m gateway.matching_engine_server 10000

# Terminal 2 – market data
python -m marketdata.md_server 10001

# Terminal 3 – risk
python -m risk_service.risk_server 10002

# Terminal 4 – gateway
python -m gateway.gateway_server 9999 10000 10001 10002

# Terminal 5 – smoke (order path + risk oversize case if added)
python -m tests.smoke_gateway 9999

# Optional – MD listener
python -m marketdata.subscriber
```

**Note:** The engine keeps one in-memory book for its lifetime. Restart the **engine** between integration runs if resting orders would affect results.

## Protocol (client ↔ gateway)

Framing (network byte order):

```text
[4 bytes length][4 bytes message type][N bytes protobuf payload]
```

`length` = size of type field + payload (see `gateway/codec.py`).

Main client types: `ADD_ORDER`, `CANCEL_ORDER`, `MODIFY_ORDER`, `ORDER_ACCEPT`, `ORDER_REJECT`, `TRADES`.  
Engine may also emit `TOP_OF_BOOK` (gateway forwards to MD, not necessarily to traders).

Risk uses a separate proto (`RiskMessageType`, `RiskSide`, …) on port 10002.

## Design decisions

- **Separate processes** for engine, gateway, MD, risk — practice service boundaries and framing  
- **Single writer** to the book (engine process / one logical matcher)  
- **Gateway worker** serializes all engine and risk RPCs (no interleaved request/response on one socket)  
- **Risk before engine** on ADD/MODIFY; rejects never hit the book  
- **MD is public tape**: trades + top-of-book; snapshot on subscribe for late joiners  
- **GFD** handled by `CancelFairy`, not inside match logic  
- **Python queues / SPSC ring** illustrate MPSC and SPSC shapes; not latency-competitive with C++ HFT  

## Testing

| Test | What it covers |
|------|----------------|
| Unit tests under `tests/` | Book / service without TCP |
| `tests/smoke_gateway.py` | Single client: match, cancel, FOK, modify, risk max size |
| `tests/test_multi.py` | Two clients, cross match |
| `marketdata.subscriber` | Live top/trades + late snapshot |

## Limitations

- Not latency-oriented (Python, threads, no kernel bypass)  
- No persistence, auth, or multi-symbol routing on the wire (risk uses defaults)  
- In-memory only; restart clears engine and risk state  
- Top-of-book / trades MD is simplified (no full L2 incremental depth yet)  

## Future work

- LevelUpdate stream from engine  
- Account/symbol on client `AddOrder` into risk  
- `END_SESSION` → `OrderService.end_session()`  
- Subprocess-started servers in CI tests  
- Stronger reject codes and metrics  

## Quick mental model

```text
Order path:  Client → Gateway → Risk → Engine → Gateway → Client
Public MD:   Engine → Gateway → MD → Subscribers
```
```

---

### What changed vs your draft

- Multi-process diagram (engine / MD / risk / gateway)  
- Correct start commands and ports  
- Risk + MD features and proto regen notes  
- Removed outdated “only `tcp_server` + in-process matcher” as the main story  
- Limitations/future work aligned with what you actually built  

Paste into `README.md` and adjust module paths if your package names differ slightly (`risk_service` vs `risk`).