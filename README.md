# 📊 NYX — Stock Market Expert Bot

Your personal AI stock analyst for the Indian market, accessible via Telegram.

## Features

- **Deep Fundamental Analysis** — Business overview, moat, valuation, financial ratios, quarterly results, management quality
- **Covered Call Strategy Analysis** — Buy Future + Sell Call position evaluation with specific strike/expiry suggestions
- **Private & Secure** — Only you can access it (user ID whitelist)
- **Local LLM** — Runs on your machine with Qwen3.6 27B via LM Studio

## Setup

### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `ALLOWED_USER_ID` — from @userinfobot
- `LLM_BASE_URL` — default `http://localhost:1234` (LM Studio)
- `LLM_MODEL` — your model name in LM Studio

### 2. Start LM Studio

1. Open LM Studio
2. Load your Qwen3.6 27B model
3. Go to the **Local Server** tab
4. Enable the **OpenAI-compatible API** server
5. Keep it running

### 3. Install Dependencies & Run

```bash
pip install -r requirements.txt
python main.py
```

### 4. Use on Telegram

Message your bot `@NYX_stockMarketExpertBot`:
- `/start` — Get started
- `/analyze RELIANCE` — Full stock analysis
- `/cc RELIANCE` — Covered call analysis
- Or just type a stock symbol directly

## Project Structure

```
stock_agent/
├── main.py              # Entry point
├── config.py            # Configuration loader
├── bot.py               # Telegram bot handler
├── analysis/
│   ├── stock_data.py    # Yahoo Finance data fetcher
│   ├── analyst.py       # Analysis engine
│   └── prompts.py       # Analyst persona prompts
├── llm/
│   └── client.py        # LLM API client
├── requirements.txt
└── .env                 # Your credentials (not in git)
```

## Disclaimer

This is for personal analysis only. Not financial advice. Always consult a SEBI-registered advisor before investing.
