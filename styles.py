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

    /* Big, thumb-friendly buttons — blue primary, green on hover/success actions */
    .stButton > button {
        width: 100%;
        min-height: 3rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 1rem;
        background-color: #0B5FBB;
        color: #FFFFFF;
        border: 1px solid #0B5FBB;
    }
    .stButton > button:hover {
        background-color: #128A46;
        border-color: #128A46;
        color: #FFFFFF;
    }
    .stButton > button:focus:not(:active) {
        color: #FFFFFF;
    }
    /* Form submit buttons get the green "confirm" treatment */
    .stFormSubmitButton > button {
        background-color: #128A46;
        border: 1px solid #128A46;
        color: #FFFFFF;
    }
    .stFormSubmitButton > button:hover {
        background-color: #0E6E38;
        border-color: #0E6E38;
    }

    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        min-height: 2.8rem;
        border-radius: 10px;
        border-color: #C7DAF0 !important;
    }

    /* Balance / summary card — blue-to-green brand gradient */
    .balance-card {
        background: linear-gradient(135deg, #0B5FBB 0%, #128A46 100%);
        color: white;
        border-radius: 18px;
        padding: 1.4rem 1.2rem;
        margin-bottom: 1rem;
    }
    .balance-card .label { font-size: 0.8rem; opacity: 0.9; }
    .balance-card .amount { font-size: 2rem; font-weight: 700; margin: 0.15rem 0; }

    .asset-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.7rem 0.9rem;
        border-radius: 12px;
        background: #EAF2FB;
        border: 1px solid #D7E7FA;
        margin-bottom: 0.5rem;
    }
    .asset-row .sym { font-weight: 700; color: #0B5FBB; }
    .asset-row .val { text-align: right; }
    .asset-row .val .fiat { font-size: 0.78rem; color: #5A6B85; }

    .badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    /* Tier badges progress from neutral -> blue -> green as verification deepens.
       Flag/pending keep red/amber since those are safety-critical warning colors. */
    .badge-tier0 { background: #E7ECF3; color: #45526B; }
    .badge-tier1 { background: #D7E7FA; color: #0B5FBB; }
    .badge-tier2 { background: #CFEAD9; color: #128A46; }
    .badge-tier3 { background: #128A46; color: #FFFFFF; }
    .badge-flag  { background: #F4CCCC; color: #990000; }
    .badge-ok    { background: #CFEAD9; color: #128A46; }
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

    h1, h2, h3 { font-weight: 700; color: #0B5FBB; }

    /* Metrics (live price tiles) */
    div[data-testid="stMetricValue"] { color: #128A46; }
</style>
"""


def inject():
    import streamlit as st
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
