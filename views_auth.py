import streamlit as st
from auth import register_user, login_user


def render_auth():
    st.markdown("## 🟢 Demo Exchange")
    st.caption("Trade BTC, ETH & USDT with Naira — securely, compliantly.")

    tab_login, tab_register = st.tabs(["Log In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            identifier = st.text_input("Email or phone")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", use_container_width=True)
            if submitted:
                user = login_user(identifier, password)
                if user:
                    st.session_state.user_id = user["id"]
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error("Invalid credentials, or account not active.")
        st.caption("Demo admin login: admin@exchange.local / Admin123!")

    with tab_register:
        with st.form("register_form"):
            full_name = st.text_input("Full legal name")
            email = st.text_input("Email address")
            phone = st.text_input("Phone number", placeholder="+2348012345678")
            password = st.text_input("Create password", type="password")
            confirm = st.text_input("Confirm password", type="password")
            agree = st.checkbox("I agree to the Terms of Service and Privacy Policy, "
                                 "and confirm I will complete identity verification (KYC) "
                                 "before transacting.")
            submitted = st.form_submit_button("Create Account", use_container_width=True)
            if submitted:
                if password != confirm:
                    st.error("Passwords do not match.")
                elif not agree:
                    st.error("You must accept the terms to continue.")
                else:
                    ok, msg = register_user(full_name, email, phone, password)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
