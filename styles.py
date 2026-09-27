"""
styles.py
Mobile-first CSS injected into the Streamlit app: narrow centered column,
big touch targets, sticky bottom nav bar that mimics a native mobile app.
"""

MOBILE_CSS = """
<style>
    /* Constrain content to a phone-width column, centered, even on desktop */
    .block-container {
        max-width: 480px;
        padding-top: 1rem;
        padding-bottom: 6rem; /* room for the bottom nav */
        margin: 0 auto;
    }

    #MainMenu, footer, header {visibility: hidden;}

    /* Big, thumb-friendly buttons */
    .stButton > button {
        width: 100%;
        min-height: 3rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 1rem;
    }

    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        min-height: 2.8rem;
        border-radius: 10px;
    }

    /* Balance / summary card */
    .balance-card {
        background: linear-gradient(135deg, #0F6E3D 0%, #0A4E2C 100%);
        color: white;
        border-radius: 18px;
        padding: 1.4rem 1.2rem;
        margin-bottom: 1rem;
    }
    .balance-card .label { font-size: 0.8rem; opacity: 0.85; }
    .balance-card .amount { font-size: 2rem; font-weight: 700; margin: 0.15rem 0; }

    .asset-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.7rem 0.9rem;
        border-radius: 12px;
        background: #F5F7F6;
        margin-bottom: 0.5rem;
    }
    .asset-row .sym { font-weight: 700; }
    .asset-row .val { text-align: right; }
    .asset-row .val .fiat { font-size: 0.78rem; color: #666; }

    .badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .badge-tier0 { background: #F3D9D9; color: #8A2A2A; }
    .badge-tier1 { background: #FCEAC3; color: #8A6A1A; }
    .badge-tier2 { background: #D9EAD3; color: #274E13; }
    .badge-tier3 { background: #CFE2F3; color: #1C4587; }
    .badge-flag  { background: #F4CCCC; color: #990000; }
    .badge-ok    { background: #D9EAD3; color: #274E13; }
    .badge-pending { background: #FFF2CC; color: #7F6000; }

    /* Sticky bottom nav */
    .bottom-nav-spacer { height: 1px; }
    div[data-testid="stHorizontalBlock"].bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        border-top: 1px solid #E5E5E5;
        padding: 0.4rem 0.5rem 0.6rem 0.5rem;
        z-index: 999;
        max-width: 480px;
        margin: 0 auto;
    }

    .txn-row {
        padding: 0.55rem 0;
        border-bottom: 1px solid #EEE;
        font-size: 0.88rem;
    }

    h1, h2, h3 { font-weight: 700; }
</style>
"""


def inject():
    import streamlit as st
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
