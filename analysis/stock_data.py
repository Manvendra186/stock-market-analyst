"""
Stock Data Fetcher — Screener.in ONLY (HTML parsing with BeautifulSoup).
No yfinance, no NSE API, no external dependencies beyond requests + bs4.
"""
import time
import random
import re
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── Config ───
SCREENER_BASE = "https://www.screener.in"
REQUEST_DELAY = 2.0
MAX_RETRIES = 2
CACHE_TTL = 300  # cache for 5 minutes

# ─── In-memory cache ───
_cache = {}

def _cache_get(symbol: str):
    symbol = symbol.upper().strip()
    if symbol in _cache:
        data, ts = _cache[symbol]
        if datetime.now() - ts < timedelta(seconds=CACHE_TTL):
            return data
    return None

def _cache_set(symbol: str, data: dict):
    _cache[symbol.upper().strip()] = (data, datetime.now())


def _fmt(value, default="N/A") -> str:
    """Format numeric values with K/M/B suffixes."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if abs(value) >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f} B"
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.2f} M"
        if abs(value) >= 1_000:
            return f"{value / 1_000:.2f} K"
        return f"{value:,.2f}"
    return str(value)


def _safe_float(val, default="N/A"):
    """Convert string/number to float, stripping ₹, %, commas, Cr, Lakh, etc."""
    if val is None or val == "N/A":
        return default
    try:
        cleaned = str(val).replace("₹", "").replace(",", "").replace("%", "").replace("Cr", "").replace("Lakh", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════
# Screener.in Session
# ═══════════════════════════════════════════════

_screener_session = None

def _get_screener_session():
    global _screener_session
    if _screener_session is None:
        import requests
        _screener_session = requests.Session()
        _screener_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
    return _screener_session


def _fetch_page(symbol: str):
    """Fetch Screener.in company page and return BeautifulSoup object."""
    from bs4 import BeautifulSoup

    time.sleep(REQUEST_DELAY + random.uniform(0.5, 1.5))
    session = _get_screener_session()
    url = f"{SCREENER_BASE}/company/{symbol.upper()}/"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


# ═══════════════════════════════════════════════
# Main Screener.in Fetcher
# ═══════════════════════════════════════════════

def fetch_stock_data(symbol: str) -> dict:
    """Fetch comprehensive stock data from Screener.in using HTML parsing."""
    symbol = symbol.upper().strip()
    logger.info(f"Fetching {symbol} from Screener.in")

    # Check cache
    cached = _cache_get(symbol)
    if cached:
        logger.info(f"Cache hit for {symbol}")
        return cached

    data = {"symbol": symbol, "company_name": "N/A"}

    for attempt in range(MAX_RETRIES):
        try:
            soup = _fetch_page(symbol)
            _parse_all(soup, data)

            # Validate we got something useful
            if data.get("company_name") and data["company_name"] != "N/A":
                logger.info(f"Screener.in success for {symbol}: {data['company_name']}")
                _cache_set(symbol, data)
                return data
            else:
                logger.warning(f"Screener.in returned no company name for {symbol}")
                break

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 3 * (2 ** attempt) + random.uniform(0, 2)
                logger.warning(f"Attempt {attempt+1} failed, retrying in {wait:.1f}s: {e}")
                time.sleep(wait)
            else:
                logger.error(f"All attempts failed for {symbol}: {e}")

    return data


def _parse_all(soup, data: dict):
    """Parse all available data from Screener.in HTML."""
    from bs4 import BeautifulSoup

    # ─── Company Name ───
    # Try h1, then og:title meta tag
    name = None
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(strip=True)
    if not name:
        og = soup.find("meta", attrs={"property": "og:title"})
        if og:
            name = og.get("content", "")
    data["company_name"] = name or data["symbol"]

    # ─── Current Price & Key Stats ───
    # Look for price in the page
    price_match = re.search(r'(?:₹|Rs\.?)\s*([\d,]+\.?\d*)', soup.get_text())
    if price_match:
        data["current_price"] = _safe_float(price_match.group(1))

    # ─── Key Ratios from the page ───
    # Screener.in shows key metrics in a structured format
    text = soup.get_text()

    # Market Cap
    mc_match = re.search(r'Market\s*Cap\s*(?:₹|Rs\.?)?\s*([\d,]+\s*(?:Cr|Lakh)?\.?\d*)', text, re.I)
    if mc_match:
        data["market_cap"] = mc_match.group(1).strip()

    # P/E Ratio
    pe_match = re.search(r'(?:Stock\s*)?P/E\s*(?:Ratio)?\s*:?\s*([\d.]+)', text, re.I)
    if pe_match:
        data["trailing_pe"] = _safe_float(pe_match.group(1))

    # Book Value
    bv_match = re.search(r'Book\s*Value\s*:?\s*(?:₹|Rs\.?)?\s*([\d.]+)', text, re.I)
    if bv_match:
        data["book_value"] = _safe_float(bv_match.group(1))

    # Dividend Yield
    dy_match = re.search(r'Dividend\s*Yield\s*:?\s*([\d.]+)', text, re.I)
    if dy_match:
        data["dividend_yield"] = _safe_float(dy_match.group(1))

    # ROCE
    roce_match = re.search(r'ROCE\s*:?\s*([\d.]+)', text, re.I)
    if roce_match:
        data["roce"] = _safe_float(roce_match.group(1))

    # ROE
    roe_match = re.search(r'ROE\s*:?\s*([\d.]+)', text, re.I)
    if roe_match:
        data["roe"] = _safe_float(roe_match.group(1))

    # 52-week High/Low
    hl_match = re.search(r'(?:High\s*/\s*Low|52\s*Week\s*(?:High|Low))\s*:?\s*(?:₹|Rs\.?)?\s*([\d.]+)\s*/\s*(?:₹|Rs\.?)?\s*([\d.]+)', text, re.I)
    if hl_match:
        data["52_week_high"] = _safe_float(hl_match.group(1))
        data["52_week_low"] = _safe_float(hl_match.group(2))

    # Face Value
    fv_match = re.search(r'Face\s*Value\s*:?\s*(?:₹|Rs\.?)?\s*([\d.]+)', text, re.I)
    if fv_match:
        data["face_value"] = _safe_float(fv_match.group(1))

    # ─── Business Description ───
    about = soup.find(id="about") or soup.find(class_=re.compile(r"about|description", re.I))
    if about:
        desc = about.get_text(strip=True)
        data["business_summary"] = desc[:500] if len(desc) > 50 else "N/A"

    # ─── Financial Tables ───
    # Parse Profit & Loss table
    pl_table = soup.find(id="profit-and-loss")
    if pl_table:
        _parse_financial_table(pl_table, data, "income")

    # Parse Balance Sheet table
    bs_table = soup.find(id="balance-sheet")
    if bs_table:
        _parse_financial_table(bs_table, data, "balance")

    # Parse Cash Flow table
    cf_table = soup.find(id="cash-flow")
    if cf_table:
        _parse_financial_table(cf_table, data, "cashflow")

    # ─── Fill missing fields with defaults ───
    _fill_defaults(data)


def _parse_financial_table(table, data: dict, table_type: str):
    """Parse a Screener.in financial table."""
    rows = table.find_all("tr")
    if not rows:
        return

    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        label = cells[0].get_text(strip=True).lower()
        values = [c.get_text(strip=True) for c in cells[1:]]

        if table_type == "income":
            if "revenue" in label or "sales" in label or "total revenue" in label:
                data["income_statement"] = {
                    "revenue": _safe_float(values[0]) if values else 0,
                }
            elif "net income" in label or "profit after tax" in label:
                if "income_statement" not in data:
                    data["income_statement"] = {}
                data["income_statement"]["net_income"] = _safe_float(values[0]) if values else 0
            elif "operating profit" in label or "ebit" in label:
                if "income_statement" not in data:
                    data["income_statement"] = {}
                data["income_statement"]["operating_income"] = _safe_float(values[0]) if values else 0

        elif table_type == "balance":
            if "total assets" in label:
                data["balance_sheet"] = {
                    "total_assets": _safe_float(values[0]) if values else 0,
                }
            elif "total equity" in label or "shareholders equity" in label:
                if "balance_sheet" not in data:
                    data["balance_sheet"] = {}
                data["balance_sheet"]["total_stockholder_equity"] = _safe_float(values[0]) if values else 0


def _fill_defaults(data: dict):
    """Set default values for fields not available from Screener.in."""
    defaults = {
        "previous_close": "N/A",
        "open_price": "N/A",
        "day_high": "N/A",
        "day_low": "N/A",
        "50_day_avg": "N/A",
        "200_day_avg": "N/A",
        "forward_pe": "N/A",
        "peg_ratio": "N/A",
        "price_to_sales": "N/A",
        "ev_to_ebitda": "N/A",
        "ev_to_revenue": "N/A",
        "enterprise_value": "N/A",
        "beta": "N/A",
        "shares_outstanding": "N/A",
        "float_shares": "N/A",
        "avg_volume_10d": "N/A",
        "isin": "N/A",
        "employees": "N/A",
        "dividend_rate": "N/A",
        "payout_ratio": "N/A",
        "total_debt": "N/A",
        "total_cash": "N/A",
        "total_debt_to_equity": "N/A",
        "current_ratio": "N/A",
        "quick_ratio": "N/A",
        "total_cash_per_share": "N/A",
        "profit_margins": "N/A",
        "operating_margins": "N/A",
        "gross_margins": "N/A",
        "revenue_growth": "N/A",
        "earnings_growth": "N/A",
        "quarterly_earnings": [],
        "insider_ownership": "N/A",
        "institutional_ownership": "N/A",
        "short_ratio": "N/A",
        "target_mean_price": "N/A",
        "target_high_price": "N/A",
        "target_low_price": "N/A",
        "recommendation_key": "N/A",
        "numberOfAnalystOpinions": "N/A",
        "insider_transactions": [],
        "options_data": {"available": False, "reason": "Not available"},
        "delivery_percentage": "N/A",
        "sector": "N/A",
        "industry": "N/A",
        "country": "India",
        "business_summary": "N/A",
        "income_statement": {},
        "balance_sheet": {},
    }

    for key, default_value in defaults.items():
        if key not in data:
            data[key] = default_value
