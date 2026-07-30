"""
Analyst Engine - Orchestrates data fetching and LLM analysis
"""
import logging
from .stock_data import fetch_stock_data
from llm.client import chat
from .prompts import SYSTEM_PROMPT, COVERED_CALL_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _format_data_for_prompt(data: dict) -> str:
    """Format fetched stock data into a clean text block for the LLM."""
    lines = []

    # ─── Company Overview ───
    lines.append("=== COMPANY OVERVIEW ===")
    lines.append(f"Name: {data.get('company_name', 'N/A')}")
    lines.append(f"Symbol: {data.get('symbol', 'N/A')}")
    lines.append(f"Sector: {data.get('sector', 'N/A')}")
    lines.append(f"Industry: {data.get('industry', 'N/A')}")
    lines.append(f"Market Cap: {data.get('market_cap', 'N/A')}")
    lines.append(f"Business Summary: {data.get('business_summary', 'N/A')[:500]}")
    lines.append("")

    # ─── Price Data ───
    lines.append("=== PRICE DATA ===")
    lines.append(f"Current Price: ₹{data.get('current_price', 'N/A')}")
    lines.append(f"Previous Close: ₹{data.get('previous_close', 'N/A')}")
    lines.append(f"Day Range: ₹{data.get('day_low', 'N/A')} - ₹{data.get('day_high', 'N/A')}")
    lines.append(f"52-Week Range: ₹{data.get('52_week_low', 'N/A')} - ₹{data.get('52_week_high', 'N/A')}")
    lines.append(f"50-Day MA: ₹{data.get('50_day_avg', 'N/A')}")
    lines.append(f"200-Day MA: ₹{data.get('200_day_avg', 'N/A')}")
    lines.append("")

    # ─── Valuation ───
    lines.append("=== VALUATION RATIOS ===")
    lines.append(f"Trailing PE: {data.get('trailing_pe', 'N/A')}")
    lines.append(f"Forward PE: {data.get('forward_pe', 'N/A')}")
    lines.append(f"PEG Ratio: {data.get('peg_ratio', 'N/A')}")
    lines.append(f"Price-to-Book: {data.get('price_to_book', 'N/A')}")
    lines.append(f"Price-to-Sales: {data.get('price_to_sales', 'N/A')}")
    lines.append(f"EV/Revenue: {data.get('ev_to_revenue', 'N/A')}")
    lines.append(f"EV/EBITDA: {data.get('ev_to_ebitda', 'N/A')}")
    lines.append("")

    # ─── Profitability ───
    lines.append("=== PROFITABILITY ===")
    lines.append(f"ROE: {data.get('roe', 'N/A')}")
    lines.append(f"ROCE (ROA): {data.get('roce', 'N/A')}")
    lines.append(f"Profit Margins: {data.get('profit_margins', 'N/A')}")
    lines.append(f"Operating Margins: {data.get('operating_margins', 'N/A')}")
    lines.append(f"Gross Margins: {data.get('gross_margins', 'N/A')}")
    lines.append(f"Revenue Growth: {data.get('revenue_growth', 'N/A')}")
    lines.append(f"Earnings Growth: {data.get('earnings_growth', 'N/A')}")
    lines.append("")

    # ─── Balance Sheet ───
    lines.append("=== BALANCE SHEET ===")
    lines.append(f"Total Debt: {data.get('total_debt', 'N/A')}")
    lines.append(f"Debt-to-Equity: {data.get('total_debt_to_equity', 'N/A')}")
    lines.append(f"Current Ratio: {data.get('current_ratio', 'N/A')}")
    lines.append(f"Quick Ratio: {data.get('quick_ratio', 'N/A')}")
    lines.append(f"Total Cash: {data.get('total_cash', 'N/A')}")
    lines.append(f"Cash per Share: ₹{data.get('total_cash_per_share', 'N/A')}")
    lines.append("")

    # ─── Dividends ───
    lines.append("=== DIVIDENDS ===")
    lines.append(f"Dividend Yield: {data.get('dividend_yield', 'N/A')}")
    lines.append(f"Dividend Rate: {data.get('dividend_rate', 'N/A')}")
    lines.append(f"Payout Ratio: {data.get('payout_ratio', 'N/A')}")
    lines.append("")

    # ─── Technical ───
    lines.append("=== TECHNICAL ===")
    lines.append(f"Beta: {data.get('beta', 'N/A')}")
    lines.append(f"Avg Volume (10D): {data.get('avg_volume_10d', 'N/A')}")
    lines.append(f"Shares Outstanding: {data.get('shares_outstanding', 'N/A')}")
    lines.append(f"Insider Ownership: {data.get('insider_ownership', 'N/A')}")
    lines.append(f"Institutional Ownership: {data.get('institutional_ownership', 'N/A')}")
    lines.append("")

    # ─── Analyst Targets ───
    lines.append("=== ANALYST TARGETS ===")
    lines.append(f"Mean Target: ₹{data.get('target_mean_price', 'N/A')}")
    lines.append(f"High Target: ₹{data.get('target_high_price', 'N/A')}")
    lines.append(f"Low Target: ₹{data.get('target_low_price', 'N/A')}")
    lines.append(f"Recommendation: {data.get('recommendation_key', 'N/A')}")
    lines.append(f"Number of Analysts: {data.get('numberOfAnalystOpinions', 'N/A')}")
    lines.append("")

    # ─── Quarterly Earnings ───
    lines.append("=== QUARTERLY EARNINGS ===")
    for q in data.get("quarterly_earnings", []):
        lines.append(f"  {q.get('date', 'N/A')}: Revenue = {q.get('revenue', 'N/A')}, Earnings = {q.get('earnings', 'N/A')}")
    lines.append("")

    # ─── Income Statement ───
    lines.append("=== LATEST INCOME STATEMENT ===")
    inc = data.get("income_statement", {})
    if inc:
        lines.append(f"  Revenue: {inc.get('revenue', 'N/A')}")
        lines.append(f"  Gross Profit: {inc.get('gross_profit', 'N/A')}")
        lines.append(f"  Operating Income: {inc.get('operating_income', 'N/A')}")
        lines.append(f"  Net Income: {inc.get('net_income', 'N/A')}")
        lines.append(f"  EBITDA: {inc.get('ebitda', 'N/A')}")
    lines.append("")

    # ─── Insider Transactions ───
    lines.append("=== RECENT INSIDER TRANSACTIONS ===")
    for txn in data.get("insider_transactions", [])[:5]:
        lines.append(f"  {txn.get('name', 'N/A')} ({txn.get('position', 'N/A')}): {txn.get('transaction_text', 'N/A')} on {txn.get('latest_trans_date', 'N/A')}")
    lines.append("")

    return "\n".join(lines)


def _format_options_data(data: dict) -> str:
    """Format options data for covered call analysis."""
    lines = []
    opt = data.get("options_data", {})

    if not opt.get("available"):
        lines.append(f"Options data not available: {opt.get('reason', 'Unknown')}")
        return "\n".join(lines)

    lines.append(f"Underlying Price: ₹{opt.get('underlying_price', 'N/A')}")
    lines.append(f"Expiry Date: {opt.get('expiry', 'N/A')}")
    lines.append("")

    lines.append("=== ATM CALLS ===")
    for call in opt.get("atm_calls", []):
        lines.append(f"  Strike: {call.get('contractPrice', 'N/A')} | "
                     f"Last: {call.get('lastPrice', 'N/A')} | "
                     f"Bid: {call.get('bid', 'N/A')} | Ask: {call.get('ask', 'N/A')} | "
                     f"IV: {call.get('impliedVolatility', 'N/A')} | "
                     f"OI: {call.get('openInterest', 'N/A')}")

    lines.append("")
    lines.append("=== OTM CALLS ===")
    for call in opt.get("otm_calls", []):
        lines.append(f"  Strike: {call.get('contractPrice', 'N/A')} | "
                     f"Last: {call.get('lastPrice', 'N/A')} | "
                     f"Bid: {call.get('bid', 'N/A')} | Ask: {call.get('ask', 'N/A')} | "
                     f"IV: {call.get('impliedVolatility', 'N/A')} | "
                     f"OI: {call.get('openInterest', 'N/A')}")

    return "\n".join(lines)


async def analyze_stock(stock_symbol: str) -> str:
    """Perform full fundamental analysis of a stock."""
    logger.info(f"Starting analysis for: {stock_symbol}")

    # Fetch data
    try:
        data = fetch_stock_data(stock_symbol)
    except Exception as e:
        logger.error(f"Error fetching data for {stock_symbol}: {e}")
        return f"❌ Could not fetch data for **{stock_symbol}**. The stock may not exist on NSE/BSE, or there may be a network issue. Please check the symbol and try again."

    # Check if stock was found
    if not data.get("company_name") or data["company_name"] == "N/A":
        return f"❌ Stock **{stock_symbol}** not found on NSE/BSE. Please check the symbol (use the NSE ticker name like RELIANCE, TCS, INFY, etc.)."

    # Build prompt
    formatted_data = _format_data_for_prompt(data)
    user_prompt = (
        f"Analyze the following stock comprehensively:\n\n"
        f"**Stock: {data['company_name']} ({data['symbol']})**\n\n"
        f"Here is the available data:\n\n"
        f"{formatted_data}\n\n"
        f"Provide your complete analysis covering all the areas mentioned in your guidelines."
    )

    # Get analysis from LLM
    return await chat(SYSTEM_PROMPT, user_prompt)


async def analyze_covered_call(stock_symbol: str) -> str:
    """Analyze whether a covered call position is advisable."""
    logger.info(f"Starting covered call analysis for: {stock_symbol}")

    # Fetch data
    try:
        data = fetch_stock_data(stock_symbol)
    except Exception as e:
        logger.error(f"Error fetching data for {stock_symbol}: {e}")
        return f"❌ Could not fetch data for **{stock_symbol}**. Please check the symbol and try again."

    # Check if stock was found
    if not data.get("company_name") or data["company_name"] == "N/A":
        return f"❌ Stock **{stock_symbol}** not found on NSE/BSE. Please check the symbol."

    # Build prompt with fundamentals + options data
    formatted_data = _format_data_for_prompt(data)
    formatted_options = _format_options_data(data)

    user_prompt = (
        f"Should I take a **Covered Call position (Buy Future + Sell Call)** on the following stock?\n\n"
        f"**Stock: {data['company_name']} ({data['symbol']})**\n\n"
        f"Here is the available fundamental data:\n\n"
        f"{formatted_data}\n\n"
        f"Here is the options data:\n\n"
        f"{formatted_options}\n\n"
        f"Analyze whether this is a good covered call opportunity. "
        f"Consider the stock's trend, volatility, options premiums, and overall risk-reward. "
        f"Give a clear GO or NO-GO recommendation with specific strike and expiry suggestions."
    )

    # Get analysis from LLM
    return await chat(COVERED_CALL_SYSTEM_PROMPT, user_prompt)
