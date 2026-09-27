"""
transactions.py
Business logic for deposits, withdrawals, and trades. Every money-movement
function here: (1) checks KYC tier + daily limit, (2) records a transaction
row, (3) moves wallet balances, (4) runs the AML rule engine.
"""

from database import get_conn
from kyc import daily_limit_for
from wallet import (
    adjust_balance, get_balances, get_live_prices_ngn, get_daily_ngn_volume,
    run_aml_checks, is_valid_external_address, LARGE_TXN_NGN_THRESHOLD,
)

TRADE_FEE_PCT = 0.005       # 0.5% trading fee
WITHDRAWAL_FEE_NGN = 50.0   # flat fee on NGN withdrawals
CRYPTO_WITHDRAWAL_FEE_PCT = 0.001  # 0.1% network/service fee on crypto withdrawals


def _insert_txn(cur, user_id, ttype, asset, amount, fee=0.0, counter_asset=None,
                 counter_amount=None, rate=None, status="completed", reference=None,
                 external_address=None):
    cur.execute(
        """INSERT INTO transactions
           (user_id, type, asset, amount, fee, counter_asset, counter_amount,
            rate, status, reference, external_address)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, ttype, asset, amount, fee, counter_asset, counter_amount,
         rate, status, reference, external_address),
    )
    return cur.lastrowid


def _check_kyc_limit(user, ngn_equiv_amount: float):
    tier = user["kyc_tier"]
    if tier == 0:
        return False, "Complete at least Tier 1 KYC (BVN) before moving funds."
    limit = daily_limit_for(tier)
    used = get_daily_ngn_volume(user["id"])
    if used + ngn_equiv_amount > limit:
        remaining = max(0, limit - used)
        return False, (f"This exceeds your daily limit for {daily_limit_for.__module__ and ''}"
                        f"Tier {tier} (NGN {limit:,.0f}/day). "
                        f"Remaining today: NGN {remaining:,.0f}. Upgrade your KYC tier for a higher limit.")
    return True, ""


# ---------------------------------------------------------------------------
# Naira deposits & withdrawals
# ---------------------------------------------------------------------------

def deposit_ngn(user, amount: float, reference: str):
    """Simulates an instant bank-transfer deposit (in production this is a
    webhook callback from Paystack/Flutterwave/Monnify confirming a transfer
    into your dedicated virtual account for the user)."""
    if amount <= 0:
        return False, "Enter a valid amount."

    ok, msg = _check_kyc_limit(user, amount)
    if not ok:
        return False, msg

    conn = get_conn()
    cur = conn.cursor()
    txn_id = _insert_txn(cur, user["id"], "deposit_ngn", "NGN", amount, reference=reference)
    conn.commit()

    adjust_balance(user["id"], "NGN", amount)
    flags = run_aml_checks(user["id"], txn_id, "deposit_ngn", amount)
    conn.commit()

    if flags:
        return True, f"Deposit received but flagged for review: {flags[0][2]}"
    return True, f"NGN {amount:,.2f} deposited successfully."


def withdraw_ngn(user, amount: float, bank_name: str, account_number: str, account_name: str):
    if amount <= 0:
        return False, "Enter a valid amount."

    balances = get_balances(user["id"])
    available = balances.get("NGN", {}).get("balance", 0)
    total_debit = amount + WITHDRAWAL_FEE_NGN
    if total_debit > available:
        return False, f"Insufficient balance. Available: NGN {available:,.2f}."

    ok, msg = _check_kyc_limit(user, amount)
    if not ok:
        return False, msg

    conn = get_conn()
    cur = conn.cursor()
    reference = f"WD-NGN-{bank_name[:3].upper()}-{account_number[-4:]}"
    txn_id = _insert_txn(
        cur, user["id"], "withdraw_ngn", "NGN", amount, fee=WITHDRAWAL_FEE_NGN,
        reference=reference, external_address=f"{bank_name} / {account_number} / {account_name}",
    )
    conn.commit()

    adjust_balance(user["id"], "NGN", -total_debit)
    flags = run_aml_checks(user["id"], txn_id, "withdraw_ngn", amount)
    conn.commit()

    if flags:
        return True, ("Withdrawal request received but placed on hold for compliance "
                       f"review: {flags[0][2]}")
    return True, (f"Withdrawal of NGN {amount:,.2f} initiated to {bank_name} "
                   f"(**** {account_number[-4:]}). Settles within a few minutes to 1 business day.")


# ---------------------------------------------------------------------------
# Crypto deposits & withdrawals
# ---------------------------------------------------------------------------

def simulate_crypto_deposit(user, asset: str, amount: float, tx_hash: str):
    """In production this fires from a blockchain-monitoring service watching
    the user's assigned deposit address (e.g. via a node, or a provider like
    Fireblocks/BitGo webhooks) after N confirmations — never from user input.
    This demo lets you simulate an inbound deposit for testing."""
    if amount <= 0:
        return False, "Enter a valid amount."

    prices = get_live_prices_ngn()
    ngn_equiv = amount * prices.get(asset, 0)

    conn = get_conn()
    cur = conn.cursor()
    txn_id = _insert_txn(cur, user["id"], "deposit_crypto", asset, amount,
                          reference=tx_hash or "simulated")
    conn.commit()

    adjust_balance(user["id"], asset, amount)
    flags = run_aml_checks(user["id"], txn_id, "deposit_crypto", ngn_equiv)
    conn.commit()

    if flags:
        return True, f"{asset} deposit detected but flagged for review: {flags[0][2]}"
    return True, f"{amount} {asset} credited to your wallet."


def withdraw_crypto(user, asset: str, amount: float, address: str):
    if amount <= 0:
        return False, "Enter a valid amount."
    if not is_valid_external_address(asset, address):
        return False, f"That doesn't look like a valid {asset} address. Double-check and try again."

    balances = get_balances(user["id"])
    available = balances.get(asset, {}).get("balance", 0)
    fee = amount * CRYPTO_WITHDRAWAL_FEE_PCT
    total_debit = amount + fee
    if total_debit > available:
        return False, f"Insufficient balance. Available: {available:.8f} {asset}."

    prices = get_live_prices_ngn()
    ngn_equiv = amount * prices.get(asset, 0)
    ok, msg = _check_kyc_limit(user, ngn_equiv)
    if not ok:
        return False, msg

    conn = get_conn()
    cur = conn.cursor()
    txn_id = _insert_txn(
        cur, user["id"], "withdraw_crypto", asset, amount, fee=fee,
        external_address=address, reference=f"WD-{asset}",
    )
    conn.commit()

    adjust_balance(user["id"], asset, -total_debit)
    flags = run_aml_checks(user["id"], txn_id, "withdraw_crypto", ngn_equiv)
    conn.commit()

    if flags:
        return True, (f"Withdrawal request received but placed on hold for compliance "
                       f"review: {flags[0][2]}")
    return True, (f"Withdrawal of {amount} {asset} to {address[:6]}...{address[-4:]} submitted. "
                   f"Network confirmation required before it leaves the exchange wallet.")


# ---------------------------------------------------------------------------
# Trading (BTC / ETH / USDT vs NGN)
# ---------------------------------------------------------------------------

def execute_trade(user, side: str, asset: str, ngn_amount: float = None, asset_amount: float = None):
    """side: 'buy' or 'sell'. Exactly one of ngn_amount / asset_amount should
    be provided (the other is computed from the live price)."""
    prices = get_live_prices_ngn()
    price = prices.get(asset)
    if not price:
        return False, "Price feed unavailable, please try again shortly."

    if ngn_amount is not None:
        gross_asset = ngn_amount / price
    elif asset_amount is not None:
        gross_asset = asset_amount
        ngn_amount = asset_amount * price
    else:
        return False, "Specify an amount."

    if ngn_amount <= 0:
        return False, "Enter a valid amount."

    fee_asset = gross_asset * TRADE_FEE_PCT
    net_asset = gross_asset - fee_asset

    balances = get_balances(user["id"])

    ok, msg = _check_kyc_limit(user, ngn_amount)
    if not ok:
        return False, msg

    conn = get_conn()
    cur = conn.cursor()

    if side == "buy":
        ngn_available = balances.get("NGN", {}).get("balance", 0)
        if ngn_amount > ngn_available:
            return False, f"Insufficient NGN balance. Available: NGN {ngn_available:,.2f}."
        adjust_balance(user["id"], "NGN", -ngn_amount)
        adjust_balance(user["id"], asset, net_asset)
        txn_id = _insert_txn(cur, user["id"], "trade_buy", asset, net_asset,
                              fee=fee_asset, counter_asset="NGN", counter_amount=ngn_amount, rate=price)
    elif side == "sell":
        asset_available = balances.get(asset, {}).get("balance", 0)
        if gross_asset > asset_available:
            return False, f"Insufficient {asset} balance. Available: {asset_available:.8f} {asset}."
        net_ngn = ngn_amount - (fee_asset * price)
        adjust_balance(user["id"], asset, -gross_asset)
        adjust_balance(user["id"], "NGN", net_ngn)
        txn_id = _insert_txn(cur, user["id"], "trade_sell", asset, gross_asset,
                              fee=fee_asset, counter_asset="NGN", counter_amount=net_ngn, rate=price)
    else:
        return False, "Invalid trade side."

    conn.commit()
    flags = run_aml_checks(user["id"], txn_id, f"trade_{side}", ngn_amount)
    conn.commit()

    action = "Bought" if side == "buy" else "Sold"
    result = (f"{action} {net_asset if side=='buy' else gross_asset:.8f} {asset} "
              f"at NGN {price:,.2f}/each.")
    if flags:
        result += f" (Flagged for review: {flags[0][2]})"
    return True, result


def get_transaction_history(user_id: int, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )
    return cur.fetchall()
