import streamlit as st
from transactions import deposit_ngn, simulate_crypto_deposit
from wallet import get_or_create_deposit_address


def render_deposit(user):
    st.markdown("## Deposit")
    if user["kyc_tier"] == 0:
        st.warning("Complete Tier 1 KYC to start depositing.")
        return

    tab_ngn, tab_crypto = st.tabs(["🇳🇬 Naira", "Crypto"])

    with tab_ngn:
        st.caption("In production: we'd assign you a dedicated virtual bank account "
                   "(via Paystack/Flutterwave/Monnify) that credits instantly on transfer. "
                   "This demo simulates that instant credit.")
        st.text_input("Virtual account number (demo)", value="9876543210", disabled=True)
        st.text_input("Bank (demo)", value="Wema Bank (Cardstel Exchange)", disabled=True)
        with st.form("ngn_deposit_form"):
            amount = st.number_input("Amount received (NGN)", min_value=0.0, step=1000.0, format="%.2f")
            reference = st.text_input("Bank transfer reference (optional)")
            submitted = st.form_submit_button("Simulate deposit confirmation", use_container_width=True)
            if submitted:
                ok, msg = deposit_ngn(user, amount, reference or "manual-sim")
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()

    with tab_crypto:
        asset = st.selectbox("Asset", ("BTC", "ETH", "USDT"), key="dep_asset")
        address = get_or_create_deposit_address(user["id"], asset)
        st.text_input(f"Your {asset} deposit address", value=address, disabled=True)
        st.caption("Send only " + asset + " to this address. Deposits require network "
                   "confirmations before crediting (simulated here as instant).")
        with st.form("crypto_deposit_form"):
            amount = st.number_input(f"Amount ({asset}) — simulated inbound", min_value=0.0,
                                      step=0.0001, format="%.6f")
            tx_hash = st.text_input("Transaction hash (optional, demo)")
            submitted = st.form_submit_button("Simulate deposit arrival", use_container_width=True)
            if submitted:
                ok, msg = simulate_crypto_deposit(user, asset, amount, tx_hash)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()
