import streamlit as st
from transactions import withdraw_ngn, withdraw_crypto, WITHDRAWAL_FEE_NGN, CRYPTO_WITHDRAWAL_FEE_PCT
from wallet import get_balances


def render_withdraw(user):
    st.markdown("## Withdraw")
    if user["kyc_tier"] == 0:
        st.warning("Complete Tier 1 KYC to start withdrawing.")
        return

    balances = get_balances(user["id"])
    tab_ngn, tab_crypto = st.tabs(["🇳🇬 Naira", "Crypto"])

    with tab_ngn:
        available = balances.get("NGN", {}).get("balance", 0)
        st.caption(f"Available: NGN {available:,.2f}  ·  Flat fee: NGN {WITHDRAWAL_FEE_NGN:.2f}")
        with st.form("ngn_withdraw_form"):
            amount = st.number_input("Amount (NGN)", min_value=0.0, step=1000.0, format="%.2f")
            bank_name = st.text_input("Bank name")
            account_number = st.text_input("Account number", max_chars=10)
            account_name = st.text_input("Account name (must match your KYC name)")
            submitted = st.form_submit_button("Request withdrawal", use_container_width=True)
            if submitted:
                ok, msg = withdraw_ngn(user, amount, bank_name, account_number, account_name)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()
        st.caption("Production note: account name should be auto-resolved and matched against "
                   "the account number via your payment processor's name-enquiry API, and only "
                   "allow withdrawal to accounts matching the verified KYC name.")

    with tab_crypto:
        asset = st.selectbox("Asset", ("BTC", "ETH", "USDT"), key="wd_asset")
        available = balances.get(asset, {}).get("balance", 0)
        st.caption(f"Available: {available:.6f} {asset}  ·  Fee: {CRYPTO_WITHDRAWAL_FEE_PCT*100:.2f}%")
        with st.form("crypto_withdraw_form"):
            amount = st.number_input(f"Amount ({asset})", min_value=0.0, step=0.0001, format="%.6f")
            address = st.text_input(f"Destination {asset} address")
            submitted = st.form_submit_button("Request withdrawal", use_container_width=True)
            if submitted:
                ok, msg = withdraw_crypto(user, asset, amount, address)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()
        st.caption("Production note: large or first-time-address withdrawals should trigger "
                   "manual review or a cooling-off period, and addresses should ideally be "
                   "allow-listed with a delay before first use (standard exchange practice).")
