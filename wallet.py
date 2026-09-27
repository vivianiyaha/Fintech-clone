"""
wallet.py
Balance management, live price fetching, and the AML transaction rule engine.
"""

import time
import requests
from database import get_conn

SUPPORTED_ASSETS = ("BTC", "ETH", "USDT")

# CoinGecko simple-price endpoint, converted to NGN. Free/no-key endpoint —
# swap for a paid market-data feed or your liquidity provider's price stream
# in production, and add a redundant fallback source.
_COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
_ID_MAP = {"BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether"}

_price_cache = {"ts": 0, "data": None}
_CACHE_TTL = 30  # seconds


def get_live_prices_ngn() -> dict:
    """Returns {'BTC': ngn_price, 'ETH': ngn_price, 'USDT': ngn_price}.
    Falls back to a fixed mock rate if the network call fails, so the app
    stays usable offline/in this sandbox."""
    now = time.time()
    if _price_cache["data"] and now - _price_cache["ts"] < _CACHE_TTL:
        return _price_cache["data"]

    fallback = {"BTC": 98_000_000.0, "ETH": 3_600_000.0, "USDT": 1_580.0}
    try:
        ids = ",".join(_ID_MAP.values())
        resp = requests.get(_COINGECKO_URL, params={"ids": ids, "vs_currencies": "ngn"}, timeout=5)
        resp.raise_for_status()
        raw = resp.json()
        prices = {sym: raw[cg_id]["ngn"] for sym, cg_id in _ID_MAP.items() if cg_id in raw}
        if len(prices) == len(_ID_MAP):
            _price_cache["data"] = prices
            _price_cache["ts"] = now
            return prices
        return fallback
    except Exception:
        return fallback


def get_balances(user_id: int) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT asset, balance, locked FROM wallets WHERE user_id = ?", (user_id,))
    return {row["asset"]: {"balance": row["balance"], "locked": row["locked"]} for row in cur.fetchall()}


def adjust_balance(user_id: int, asset: str, delta: float, locked_delta: float = 0.0):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE wallets SET balance = balance + ?, locked = locked + ? WHERE user_id = ? AND asset = ?",
        (delta, locked_delta, user_id, asset),
    )
    conn.commit()


def get_or_create_deposit_address(user_id: int, asset: str) -> str:
    """Returns a mock deposit address. In production this must call your
    custody provider / node (e.g. Fireblocks, BitGo, or your own hot wallet
    service) to generate a real, monitored address per user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT address FROM crypto_addresses WHERE user_id = ? AND asset = ?",
        (user_id, asset),
    )
    row = cur.fetchone()
    if row:
        return row["address"]

    prefix = {"BTC": "bc1q", "ETH": "0x", "USDT": "0x"}.get(asset, "addr_")
    mock_address = prefix + f"{user_id:08x}demo{asset.lower()}0000000000"
    cur.execute(
        "INSERT INTO crypto_addresses (user_id, asset, address) VALUES (?, ?, ?)",
        (user_id, asset, mock_address),
    )
    conn.commit()
    return mock_address


def is_valid_external_address(asset: str, address: str) -> bool:
    """Very basic format validation only — NOT a substitute for real address
    checksum validation or an allow-listing / travel-rule check."""
    address = address.strip()
    if asset == "BTC":
        return bool(address) and (address.startswith(("1", "3", "bc1")) and 25 <= len(address) <= 62)
    if asset in ("ETH", "USDT"):
        return address.startswith("0x") and len(address) == 42
    return False


# ---------------------------------------------------------------------------
# AML rule engine
# ---------------------------------------------------------------------------

LARGE_TXN_NGN_THRESHOLD = 5_000_000     # single-transaction alert threshold
VELOCITY_WINDOW_MINUTES = 60
VELOCITY_MAX_TXNS = 6                    # max transactions per hour before flagging


def run_aml_checks(user_id: int, txn_id: int, txn_type: str, amount_ngn_equiv: float):
    """Runs simple, explainable rules against a just-created transaction and
    opens aml_flags rows for anything suspicious. Returns list of triggered rules.

    Production systems should replace/augment this with a real transaction
    monitoring vendor (e.g. ComplyAdvantage, Sardine, Chainalysis for on-chain
    exposure) and a documented, risk-based rule set signed off by compliance.
    """
    conn = get_conn()
    cur = conn.cursor()
    triggered = []

    if amount_ngn_equiv >= LARGE_TXN_NGN_THRESHOLD:
        triggered.append(("large_transaction", "high",
                           f"Single transaction of ~NGN {amount_ngn_equiv:,.0f} exceeds threshold."))

    cur.execute(
        """SELECT COUNT(*) as c FROM transactions
           WHERE user_id = ? AND created_at >= datetime('now', ?)""",
        (user_id, f"-{VELOCITY_WINDOW_MINUTES} minutes"),
    )
    recent_count = cur.fetchone()["c"]
    if recent_count > VELOCITY_MAX_TXNS:
        triggered.append(("velocity", "medium",
                           f"{recent_count} transactions in the last {VELOCITY_WINDOW_MINUTES} minutes."))

    for rule, severity, note in triggered:
        cur.execute(
            """INSERT INTO aml_flags (transaction_id, user_id, rule_triggered, severity, note)
               VALUES (?, ?, ?, ?, ?)""",
            (txn_id, user_id, rule, severity, note),
        )
        cur.execute("UPDATE transactions SET status = 'flagged' WHERE id = ?", (txn_id,))

    conn.commit()
    return triggered


def get_daily_ngn_volume(user_id: int) -> float:
    """Sum of the NGN-equivalent value of today's deposits/withdrawals/trades,
    used to enforce the KYC tier's daily limit."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT COALESCE(SUM(
               CASE WHEN asset = 'NGN' THEN amount
                    WHEN counter_asset = 'NGN' THEN counter_amount
                    ELSE 0 END
           ), 0) as total
           FROM transactions
           WHERE user_id = ? AND date(created_at) = date('now')
             AND status != 'rejected'""",
        (user_id,),
    )
    return cur.fetchone()["total"]
