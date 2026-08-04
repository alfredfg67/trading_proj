# Trading Platform

A small asynchronous trading simulator built with **FastAPI**, **SQLAlchemy (async)**, and a **Streamlit** analytics dashboard. It accepts orders through a REST API, "fills" them asynchronously via a background worker, records the resulting trades, and sends a Telegram alert for every executed trade.

## Features

- REST API to submit and query orders and trades
- Asynchronous order-processing worker (in-process queue, no external broker)
- Simulated market execution (80% fill rate, ±1% slippage)
- Trade analytics endpoint (win rate, total/average profit, volume)
- Streamlit dashboard with an equity curve and recent-trades table
- Telegram notifications on trade execution

## Architecture

```
Client / dashboard
      │  HTTP
      ▼
FastAPI app (app/main.py)
      │
      ├─ /api/v1/orders   → create & fetch orders (app/api/v1/endpoints/orders.py)
      ├─ /api/v1/trades   → list recent trades      (app/api/v1/endpoints/trades.py)
      └─ /api/v1/stats    → aggregate metrics        (app/api/v1/endpoints/stats.py)
                │
                ▼
      In-memory event queue (app/core/event_queue.py)
                │
                ▼
   Background worker (app/services/order_processor.py)
        - simulates market fill
        - writes Trade rows
        - triggers Telegram alert (app/services/telegram_notifier.py)
```

On startup, `app/main.py` creates the database tables and launches the background worker as an asyncio task — no separate worker process or message broker (e.g. Celery/Redis) is required.

## Project layout

```
trading_platform/
├── app/
│   ├── main.py                 # FastAPI app, lifespan (DB init + worker startup)
│   ├── core/
│   │   ├── config.py           # Settings loaded from .env (pydantic-settings)
│   │   ├── database.py         # Async SQLAlchemy engine/session setup
│   │   └── event_queue.py      # In-process asyncio.Queue used to hand off new orders
│   ├── models/
│   │   ├── orders.py           # Order ORM model + OrderStatus enum
│   │   └── trades.py           # Trade ORM model
│   ├── schemas/
│   │   ├── order.py            # Pydantic request/response schemas for orders
│   │   └── trade.py            # Pydantic response schema for trades
│   ├── api/v1/
│   │   ├── router.py           # Combines the endpoint routers under /api/v1
│   │   └── endpoints/
│   │       ├── orders.py       # POST /orders, GET /orders/{id}
│   │       ├── trades.py       # GET /trades
│   │       └── stats.py        # GET /stats
│   ├── services/
│   │   ├── order_processor.py  # Background worker: simulates fills, creates trades
│   │   ├── analytics.py        # Computes win rate / profit metrics with pandas
│   │   └── telegram_notifier.py# Sends a Telegram message on trade execution
│   └── dashboard/
│       └── app.py              # Streamlit dashboard (reads the REST API)
├── docker-compose.yml          # Optional Postgres service for local development
├── requirements.txt
├── .env.example                # Template for required environment variables
└── .gitignore
```

## Requirements

- Python 3.11+
- (Optional) Docker, if you want to run Postgres via `docker-compose.yml` instead of SQLite

## Setup

1. **Clone and install dependencies**

   ```bash
   git clone https://github.com/alfredfg67/trading_proj.git
   cd trading_proj/trading_platform
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Copy the example file and fill in your own values:

   ```bash
   cp .env.example .env
   ```

   | Variable | Required | Description |
   |---|---|---|
   | `DATABASE_URL` | Yes | Async SQLAlchemy connection string, e.g. `sqlite+aiosqlite:///./trading.db` or `postgresql+asyncpg://user:pass@localhost:5432/trading_db` |
   | `TELEGRAM_BOT_TOKEN` | Yes | Bot token from [@BotFather](https://t.me/BotFather) |
   | `TELEGRAM_CHAT_ID` | No | Chat/channel ID to receive trade alerts. If omitted, notifications are silently skipped |

   > ⚠️ Never commit your real `.env` file. It's already excluded via `.gitignore`.

3. **(Optional) Start Postgres with Docker**

   ```bash
   docker-compose up -d
   ```

   This starts a Postgres 15 instance on `localhost:5432` with database `trading_db`, user `trading_user`. Update `DATABASE_URL` in `.env` to point at it if you use this instead of SQLite.

## Running the app

**API server:**

```bash
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`. Interactive docs are available at `http://localhost:8000/docs`.

**Dashboard** (in a separate terminal, with the API already running):

```bash
streamlit run app/dashboard/app.py
```

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/orders/` | Create an order (`symbol`, `side`, `quantity`, `price`); queues it for async execution |
| `GET` | `/api/v1/orders/{order_id}` | Fetch a single order by ID |
| `GET` | `/api/v1/trades/` | List the 100 most recent trades |
| `GET` | `/api/v1/stats/` | Aggregate metrics: trade count, total/average profit, win rate, total volume |

**Example: create an order**

```bash
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{"symbol": "EURUSD", "side": "buy", "quantity": 1000, "price": 1.085}'
```

The order is created with status `pending`, then picked up by the background worker within moments. It resolves to `executed` (with a corresponding `Trade` row and a Telegram alert) 80% of the time, or `cancelled` otherwise — this is a simulated fill, not a real broker connection.

## Notes & limitations

- **Simulated execution only.** `order_processor.py` uses `random.random()` to decide fills and slippage; there's no real exchange/broker integration.
- **In-memory queue.** The event queue lives in process memory (`asyncio.Queue`), so queued-but-unprocessed orders are lost on restart, and this won't scale beyond a single process. Swapping in Redis/RabbitMQ + Celery would be the natural next step for production use.
- **SQLite by default.** `docker-compose.yml` provisions Postgres, but nothing wires `DATABASE_URL` to it automatically — you must set it yourself in `.env`.

## License

No license file is currently included in this repository. Add one (e.g. MIT) if you intend for others to reuse this code.
