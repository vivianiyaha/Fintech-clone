"""
app.py
Entry point. Run with:  streamlit run app.py

DEMO EXCHANGE-style Naira/Crypto exchange demo:
- BTC / ETH / USDT trading against NGN with live reference prices
- Naira and crypto deposits & withdrawals
- Tiered KYC (BVN -> NIN+ID -> enhanced due diligence) with daily limits
- AML rule engine (large-transaction + velocity flags) with a compliance review queue
- Mobile-first layout with a sticky bottom nav

See README.md for the production-readiness checklist before handling real funds.
"""

import streamlit as st
from database import init_db, seed_admin
from auth import get_user
import styles

from views_auth import render_auth
from views_dashboard import render_dashboard
from views_kyc import render_kyc
from views_trade import render_trade
from views_deposit import render_deposit
from views_withdraw import render_withdraw
from views_admin import render_admin

st.set_page_config(page_title="DEMO EXCHANGE", page_icon="🔵", layout="centered")

init_db()
seed_admin()
styles.inject()

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "page" not in st.session_state:
    st.session_state.page = "home"


def logout():
    st.session_state.user_id = None
    st.session_state.page = "home"
    st.rerun()


def bottom_nav(is_admin: bool):
    items = [
        ("home", "🏠", "Home"),
        ("trade", "🔁", "Trade"),
        ("deposit", "⬇️", "Deposit"),
        ("withdraw", "⬆️", "Withdraw"),
        ("kyc", "🪪", "KYC"),
    ]
    if is_admin:
        items.append(("admin", "🛡️", "Admin"))

    cols = st.columns(len(items))
    for col, (key, icon, label) in zip(cols, items):
        with col:
            active = st.session_state.page == key
            btn_label = f"**{icon}**\n{label}" if active else f"{icon}\n{label}"
            if st.button(btn_label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()


def main():
    if not st.session_state.user_id:
        render_auth()
        return

    user = get_user(st.session_state.user_id)
    if not user:
        logout()
        return

    top_l, top_r = st.columns([4, 1])
    with top_l:
        st.caption(f"👋 {user['full_name'].split()[0]}")
    with top_r:
        if st.button("Log out", use_container_width=True):
            logout()

    page = st.session_state.page
    if page == "home":
        render_dashboard(user)
    elif page == "trade":
        render_trade(user)
    elif page == "deposit":
        render_deposit(user)
    elif page == "withdraw":
        render_withdraw(user)
    elif page == "kyc":
        render_kyc(user)
    elif page == "admin" and user["is_admin"]:
        render_admin(user)
    else:
        st.session_state.page = "home"
        st.rerun()

    st.markdown('<div class="bottom-nav-spacer"></div>', unsafe_allow_html=True)
    with st.container():
        bottom_nav(bool(user["is_admin"]))


if __name__ == "__main__":
    main()
