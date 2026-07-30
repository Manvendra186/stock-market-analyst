"""
Telegram Bot Handler
"""
import logging
import re
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_ID
from analysis.analyst import analyze_stock, analyze_covered_call

logger = logging.getLogger(__name__)

# ─── State tracking per user ───
user_states = {}  # {user_id: "waiting_for_stock" | "waiting_for_cc_stock" | None}

# ─── Patterns for covered call detection ───
CC_KEYWORDS = re.compile(
    r"(covered\s*call|sell\s*call|buy\s*futur|write\s*call|options\s*strategy|f&O|f.and.O|futures.*call)",
    re.IGNORECASE,
)


def _is_allowed(user_id: int) -> bool:
    """Check if user is authorized."""
    if ALLOWED_USER_ID == 0:
        logger.warning("ALLOWED_USER_ID not configured! Blocking all users.")
        return False
    return user_id == ALLOWED_USER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        await update.message.reply_text("🔒 Access denied. This bot is private.")
        return

    welcome = (
        "📊 *Welcome to NYX — Your Stock Market Expert*\n\n"
        "I'm your personal stock analyst with 20+ years of Indian market experience.\n\n"
        "*What I can do:*\n"
        "🔍 `/analyze` — Deep fundamental analysis of any stock\n"
        "📈 `/cc` — Covered call strategy analysis (Buy Future + Sell Call)\n"
        "❓ `/help` — Show commands again\n\n"
        "Just send a stock symbol (e.g., RELIANCE, TCS, INFY) or use the commands above.\n\n"
        "_Disclaimer: Analysis only, not financial advice._"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    msg = (
        "📋 *NYX Commands*\n\n"
        "🔍 `/analyze` — Full fundamental stock analysis\n"
        "   - Business overview, moat, valuation, financial ratios\n"
        "   - Quarterly results, management quality, risks\n"
        "   - Clear BUY/HOLD/SELL recommendation\n\n"
        "📈 `/cc` — Covered call position analysis\n"
        "   - Buy Future + Sell Call strategy review\n"
        "   - Strike & expiry suggestions\n"
        "   - Risk assessment and GO/NO-GO verdict\n\n"
        "💡 *Tip:* You can also just type a stock name directly and I'll analyze it!\n\n"
        "🔒 Only authorized users can access this bot."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command."""
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        await update.message.reply_text("🔒 Access denied.")
        return

    user_states[user_id] = "waiting_for_stock"
    await update.message.reply_text(
        "🔍 *Stock Analysis*\n\n"
        "Enter the stock symbol (NSE ticker):\n"
        "_e.g., RELIANCE, TCS, INFY, HDFCBANK, WIPRO_"
    )


async def cc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cc (covered call) command."""
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        await update.message.reply_text("🔒 Access denied.")
        return

    user_states[user_id] = "waiting_for_cc_stock"
    await update.message.reply_text(
        "📈 *Covered Call Analysis*\n\n"
        "Enter the stock symbol (NSE ticker):\n"
        "_e.g., RELIANCE, TCS, INFY, HDFCBANK_"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages (stock symbols)."""
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        await update.message.reply_text("🔒 Access denied.")
        return

    text = update.message.text.strip().upper()
    state = user_states.get(user_id)

    # Detect covered call intent
    is_cc = CC_KEYWORDS.search(text) or state == "waiting_for_cc_stock"

    # Extract stock symbol
    stock_symbol = _extract_symbol(text)

    if not stock_symbol:
        if state:
            await update.message.reply_text(
                "❓ Please enter a valid NSE stock symbol.\n"
                "_e.g., RELIANCE, TCS, INFY_"
            )
            return
        # Auto-detect: if they mention covered call keywords, ask for stock
        if is_cc:
            user_states[user_id] = "waiting_for_cc_stock"
            await update.message.reply_text(
                "📈 You want a covered call analysis!\n"
                "Enter the stock symbol: _e.g., RELIANCE, TCS_"
            )
            return
        # Default: fundamental analysis
        await update.message.reply_text(
            "🤔 I didn't understand. Please send a stock symbol or use:\n"
            "🔍 `/analyze` for fundamental analysis\n"
            "📈 `/cc` for covered call analysis"
        )
        return

    # Send processing message
    await update.message.reply_text(f"⏳ Analyzing **{stock_symbol}**... This may take a moment.", parse_mode="Markdown")

    try:
        if is_cc:
            result = await analyze_covered_call(stock_symbol)
        else:
            result = await analyze_stock(stock_symbol)

        # Telegram has a 4096 char limit per message — split if needed
        if len(result) > 4000:
            await _send_long_message(update, result)
        else:
            await update.message.reply_text(result, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        await update.message.reply_text(
            "❌ Analysis failed. Please try again."
        )
    finally:
        user_states[user_id] = None


def _extract_symbol(text: str) -> str:
    """Extract stock symbol from user message."""
    # Clean up common patterns
    text = text.strip()

    # Remove common prefixes
    text = re.sub(r"^(analyze|analyse|stock|symbol|ticker|check|review|cc|covered\s*call)\s*", "", text, flags=re.IGNORECASE)
    text = text.strip()

    # Remove non-alphanumeric characters but keep the symbol
    symbol = re.sub(r"[^A-Z0-9]", "", text)

    # Validate: should be 1-10 chars (typical NSE symbol length)
    if symbol and 1 <= len(symbol) <= 10:
        return symbol.upper()

    return ""


async def _send_long_message(update, text: str):
    """Split long messages at section boundaries for clean Telegram display."""
    chunk_size = 3800

    # Split into sections by detecting emoji headings or ━━ dividers
    sections = re.split(r'(?=(?:🏢|🏰|📊|📐|💰|👔|📅|⚠️|✅|📈|📉|🎯|🔄|📌|━━━━━━━━))', text)
    sections = [s.strip() for s in sections if s.strip()]

    chunks = []
    current = ""

    for section in sections:
        if len(current) + len(section) <= chunk_size:
            current += section + "\n\n" if current else section
        else:
            if current:
                chunks.append(current.strip())
            current = section

    if current:
        chunks.append(current.strip())

    # Fallback: if any chunk is still too long, force-split at newlines
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
        else:
            # Force split
            start = 0
            while start < len(chunk):
                end = start + chunk_size
                if end >= len(chunk):
                    final_chunks.append(chunk[start:])
                    break
                break_point = chunk.rfind("\n", start, end)
                if break_point == -1:
                    break_point = end
                final_chunks.append(chunk[start:break_point])
                start = break_point

    for i, chunk in enumerate(final_chunks):
        if i == 0:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        else:
            await update.message.reply_text(chunk, parse_mode="Markdown")


def create_application() -> Application:
    """Create and configure the Telegram bot application."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("cc", cc_command))

    # All text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return application
