"""
NYX Stock Market Expert Bot
Main entry point
"""
import logging
import sys
from bot import create_application
from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_ID

# ─── Logging ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("nyx_agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("NYX")


def validate_config():
    """Check that required config is set."""
    issues = []

    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        issues.append("🔑 TELEGRAM_BOT_TOKEN not set in .env file")

    if ALLOWED_USER_ID == 0:
        issues.append("👤 ALLOWED_USER_ID not set in .env file")

    if issues:
        print("\n" + "=" * 50)
        print("⚠️  CONFIGURATION ISSUES")
        print("=" * 50)
        for issue in issues:
            print(f"  {issue}")
        print("\nPlease edit the `.env` file with your credentials.")
        print("Copy `.env.example` to `.env` and fill in the values.")
        print("=" * 50 + "\n")
        return False

    return True


async def check_llm():
    """Quick check if LLM is reachable."""
    import httpx
    from config import LLM_BASE_URL
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LLM_BASE_URL}/v1/models")
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                model_names = [m["id"] for m in models]
                logger.info(f"✅ LLM connected! Available models: {model_names}")
                return True
    except Exception as e:
        logger.warning(f"⚠️  Could not connect to LLM at {LLM_BASE_URL}: {e}")
        logger.warning("Make sure LM Studio is running with the OpenAI-compatible API enabled.")
        return False
    return False


def main():
    """Start the NYX bot."""
    print("\n" + "📊" * 20)
    print("  NYX — Stock Market Expert Bot")
    print("  Your personal Indian market analyst")
    print("📊" * 20 + "\n")

    # Validate config
    if not validate_config():
        sys.exit(1)

    # Check LLM
    import asyncio
    llm_ok = asyncio.run(check_llm())
    if not llm_ok:
        print("\n⚠️  WARNING: LLM not reachable. The bot will start but analyses will fail.")
        print("   Start LM Studio and enable the OpenAI-compatible API server.\n")

    # Create and run bot
    logger.info("🚀 Starting NYX bot...")
    app = create_application()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
