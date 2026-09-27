import streamlit as st
from wallet import get_balances, get_live_prices_ngn
from transactions import execute_trade, TRADE_FEE_PCT


def render_trade(user):
    st.markdown("## Trade")
    if user["kyc_tier"] == 0:
        st.warning("Complete Tier 1 KYC to start trading.")
        return

    prices = get_live_prices_ngn()
    balances = get_balances(user["id"])

    asset = st.selectbox("Asset", ("BTC", "ETH", "USDT"))
    price = prices.get(asset, 0)
    st.metric(f"{asset}/NGN", f"₦{price:,.2f}", help="Live reference price. 0.5% trading fee applies.")

    side = st.radio("Action", ("Buy", "Sell"), horizontal=True)
    mode = st.radio("Enter amount in", ("NGN", asset), horizontal=True)

    ngn_bal = balances.get("NGN", {}).get("balance", 0)
    asset_bal = balances.get(asset, {}).get("balance", 0)
    st.caption(f"Available: NGN {ngn_bal:,.2f}  ·  {asset_bal:.6f} {asset}")

    with st.form("trade_form"):
        if mode == "NGN":
            amount = st.number_input("Amount (NGN)", min_value=0.0, step=1000.0, format="%.2f")
            est = amount / price if price else 0
            st.caption(f"≈ {est:.6f} {asset} before fees")
        else:
            amount = st.number_input(f"Amount ({asset})", min_value=0.0, step=0.0001, format="%.6f")
            est = amount * price
            st.caption(f"≈ NGN {est:,.2f}")

        st.caption(f"Fee: {TRADE_FEE_PCT*100:.1f}% of the {asset} side")
        submitted = st.form_submit_button(f"{side} {asset}", use_container_width=True)

        if submitted:
            if mode == "NGN":
                ok, msg = execute_trade(user, side.lower(), asset, ngn_amount=amount)
            else:
                ok, msg = execute_trade(user, side.lower(), asset, asset_amount=amount)
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()
