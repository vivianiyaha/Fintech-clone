import streamlit as st
from wallet import get_balances, get_live_prices_ngn
from kyc import tier_label, daily_limit_for, latest_kyc_status
from transactions import get_transaction_history

TIER_BADGE_CLASS = {0: "badge-tier0", 1: "badge-tier1", 2: "badge-tier2", 3: "badge-tier3"}
ASSET_ICON = {"BTC": "₿", "ETH": "Ξ", "USDT": "₮"}


def render_dashboard(user):
    balances = get_balances(user["id"])
    prices = get_live_prices_ngn()
    ngn_balance = balances.get("NGN", {}).get("balance", 0)

    crypto_total_ngn = sum(
        balances.get(a, {}).get("balance", 0) * prices.get(a, 0) for a in ("BTC", "ETH", "USDT")
    )

    st.markdown(
        f"""<div class="balance-card">
                <div class="label">Total estimated balance</div>
                <div class="amount">NGN {ngn_balance + crypto_total_ngn:,.2f}</div>
                <div class="label">Cash: NGN {ngn_balance:,.2f} · Crypto: NGN {crypto_total_ngn:,.2f}</div>
            </div>""",
        unsafe_allow_html=True,
    )

    tier = user["kyc_tier"]
    badge_class = TIER_BADGE_CLASS.get(tier, "badge-tier0")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(
            f'<span class="badge {badge_class}">{tier_label(tier)}</span>',
            unsafe_allow_html=True,
        )
    with col2:
        st.caption(f"Daily limit: NGN {daily_limit_for(tier):,.0f}")

    if tier == 0:
        st.warning("Verify your identity to start depositing, trading, and withdrawing.")
        if st.button("Start KYC verification", use_container_width=True):
            st.session_state.page = "kyc"
            st.rerun()

    kyc_status = latest_kyc_status(user["id"])
    if kyc_status and kyc_status["status"] == "pending":
        st.info("Your KYC submission is under compliance review.")

    st.markdown("### Your assets")
    for asset in ("BTC", "ETH", "USDT"):
        bal = balances.get(asset, {}).get("balance", 0)
        locked = balances.get(asset, {}).get("locked", 0)
        price = prices.get(asset, 0)
        st.markdown(
            f"""<div class="asset-row">
                    <div><span class="sym">{ASSET_ICON.get(asset,'')} {asset}</span></div>
                    <div class="val">{bal:.6f} {asset}<br/>
                        <span class="fiat">≈ NGN {bal*price:,.2f}{' · ' + format(locked, '.6f') + ' locked' if locked else ''}</span>
                    </div>
                </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("### Live prices")
    pcols = st.columns(3)
    for i, asset in enumerate(("BTC", "ETH", "USDT")):
        with pcols[i]:
            st.metric(asset, f"₦{prices.get(asset,0):,.0f}")

    st.markdown("### Recent activity")
    history = get_transaction_history(user["id"], limit=8)
    if not history:
        st.caption("No transactions yet.")
    for txn in history:
        status_badge = {
            "completed": "badge-ok", "pending": "badge-pending", "flagged": "badge-flag",
            "rejected": "badge-flag",
        }.get(txn["status"], "badge-pending")
        st.markdown(
            f"""<div class="txn-row">
                    {txn['type'].replace('_',' ').title()} — {txn['amount']:.6f} {txn['asset']}
                    <span class="badge {status_badge}" style="float:right;">{txn['status']}</span><br/>
                    <span style="color:#888;font-size:0.78rem;">{txn['created_at']}</span>
                </div>""",
            unsafe_allow_html=True,
        )
