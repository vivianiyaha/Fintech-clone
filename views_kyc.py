import streamlit as st
from kyc import submit_kyc, latest_kyc_status, tier_label, daily_limit_for


def render_kyc(user):
    st.markdown("## Identity Verification")
    st.caption("Nigerian VASPs are expected to verify identity in tiers, in line with "
               "CBN/SEC and NFIU AML guidance. Higher tiers unlock higher daily limits.")

    current_tier = user["kyc_tier"]
    st.markdown(f"**Current level:** {tier_label(current_tier)} "
                f"(NGN {daily_limit_for(current_tier):,.0f}/day)")

    status = latest_kyc_status(user["id"])
    if status and status["status"] == "pending":
        st.info(f"Your Tier {status['tier_requested']} submission is pending compliance review.")

    next_tier = min(current_tier + 1, 3)
    if current_tier >= 3:
        st.success("You're at the highest verification tier.")
        return

    st.markdown(f"### Apply for Tier {next_tier}")

    with st.form("kyc_form"):
        full_name = st.text_input("Full legal name (must match your ID)", value=user["full_name"])
        bvn = nin = id_type = id_number = address = ""

        if next_tier == 1:
            bvn = st.text_input("Bank Verification Number (BVN)", max_chars=11,
                                 help="11-digit BVN, verified against NIBSS in production.")
        if next_tier == 2:
            bvn = st.text_input("BVN", max_chars=11)
            nin = st.text_input("National Identity Number (NIN)", max_chars=11)
            id_type = st.selectbox("Government-issued ID", ["National ID Card", "Driver's License",
                                                              "International Passport", "Voter's Card"])
            id_number = st.text_input("ID number")
            st.file_uploader("Upload ID document (front)", type=["png", "jpg", "jpeg", "pdf"])
            st.file_uploader("Selfie for liveness check", type=["png", "jpg", "jpeg"])
        if next_tier == 3:
            address = st.text_area("Residential address")
            st.file_uploader("Proof of address (utility bill / bank statement, <3 months)",
                              type=["png", "jpg", "jpeg", "pdf"])
            st.text_area("Source of funds description",
                         help="Briefly describe the origin of funds you plan to trade (e.g. salary, business revenue).")

        is_pep = st.checkbox("I am a Politically Exposed Person (PEP) or a close associate of one.")

        submitted = st.form_submit_button("Submit for verification", use_container_width=True)
        if submitted:
            ok, msg = submit_kyc(
                user["id"], next_tier, full_name, bvn=bvn, nin=nin,
                id_type=id_type, id_number=id_number, address=address, is_pep=is_pep,
            )
            (st.success if ok else st.error)(msg)
            if ok and "Verified" in msg:
                st.rerun()
