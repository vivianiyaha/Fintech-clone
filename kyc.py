"""
kyc.py
Tiered KYC system and the daily transaction limits tied to each tier.

Tier 0 (Unverified) : browse only, no deposits/withdrawals/trades
Tier 1 (Basic)       : BVN + phone confirmed        -> up to NGN 100,000 / day
Tier 2 (Standard)    : + NIN + government ID + selfie -> up to NGN 2,000,000 / day
Tier 3 (Enhanced)    : + proof of address + source-of-funds -> up to NGN 20,000,000 / day

This mirrors the tiered-KYC approach Nigerian VASPs typically use to stay aligned
with CBN/SEC and NFIU expectations, but the thresholds here are illustrative —
a real deployment must set these per your compliance officer's risk assessment
and current regulation, and BVN/NIN must be verified against NIBSS/NIMC APIs
(or a licensed KYC vendor) rather than accepted at face value as this demo does.
"""

from database import get_conn

TIER_LIMITS = {
    0: {"label": "Unverified", "daily_ngn": 0},
    1: {"label": "Basic (BVN)", "daily_ngn": 100_000},
    2: {"label": "Standard (NIN + ID)", "daily_ngn": 2_000_000},
    3: {"label": "Enhanced (Full EDD)", "daily_ngn": 20_000_000},
}

# Simple local sanctions/PEP watchlist stub for the demo.
# In production this must call a real screening provider (e.g. ComplyAdvantage,
# Refinitiv World-Check, or the NFIU/UN consolidated sanctions list).
_MOCK_WATCHLIST = {"john sanctioned doe", "jane blocked smith"}


def screen_name(full_name: str) -> bool:
    """Returns True if the name hits the (mock) sanctions watchlist."""
    return full_name.strip().lower() in _MOCK_WATCHLIST


def daily_limit_for(tier: int) -> int:
    return TIER_LIMITS.get(tier, TIER_LIMITS[0])["daily_ngn"]


def tier_label(tier: int) -> str:
    return TIER_LIMITS.get(tier, TIER_LIMITS[0])["label"]


def submit_kyc(user_id: int, tier_requested: int, full_name: str, bvn: str = "",
               nin: str = "", id_type: str = "", id_number: str = "",
               address: str = "", is_pep: bool = False):
    """Records a KYC submission. Tiers 1-2 auto-approve in this demo (simulating
    an instant BVN/NIN verification call); tier 3 always routes to manual review
    since it involves enhanced due diligence. A sanctions hit always forces
    manual review regardless of tier."""
    conn = get_conn()
    cur = conn.cursor()

    sanctions_hit = screen_name(full_name)
    auto_approve = tier_requested in (1, 2) and not sanctions_hit and not is_pep
    status = "approved" if auto_approve else "pending"

    cur.execute(
        """INSERT INTO kyc_records
           (user_id, tier_requested, bvn, nin, id_type, id_number, address,
            is_pep, sanctions_hit, status, reviewed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, tier_requested, bvn, nin, id_type, id_number, address,
         int(is_pep), int(sanctions_hit), status,
         "datetime('now')" if auto_approve else None),
    )

    if auto_approve:
        cur.execute("UPDATE users SET kyc_tier = ? WHERE id = ?", (tier_requested, user_id))

    conn.commit()

    if sanctions_hit or is_pep:
        return False, ("Submission received but flagged for enhanced review "
                        "(PEP / watchlist match). This can take 1-3 business days.")
    if auto_approve:
        return True, f"Verified! You're now {tier_label(tier_requested)}."
    return True, "Submitted for manual compliance review (Tier 3 requires human sign-off)."


def latest_kyc_status(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM kyc_records WHERE user_id = ? ORDER BY submitted_at DESC LIMIT 1",
        (user_id,),
    )
    return cur.fetchone()


def pending_kyc_queue():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT kyc_records.*, users.full_name, users.email
           FROM kyc_records JOIN users ON users.id = kyc_records.user_id
           WHERE kyc_records.status = 'pending' ORDER BY submitted_at ASC"""
    )
    return cur.fetchall()


def review_kyc(kyc_id: int, approve: bool, reviewer_note: str, admin_email: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM kyc_records WHERE id = ?", (kyc_id,))
    record = cur.fetchone()
    if not record:
        return False, "Record not found."

    new_status = "approved" if approve else "rejected"
    cur.execute(
        """UPDATE kyc_records SET status = ?, reviewer_note = ?, reviewed_at = datetime('now')
           WHERE id = ?""",
        (new_status, reviewer_note, kyc_id),
    )
    if approve:
        cur.execute(
            "UPDATE users SET kyc_tier = ? WHERE id = ?",
            (record["tier_requested"], record["user_id"]),
        )
    cur.execute(
        "INSERT INTO audit_log (actor, action, target, details) VALUES (?, ?, ?, ?)",
        (admin_email, f"kyc_{new_status}", f"user:{record['user_id']}", reviewer_note),
    )
    conn.commit()
    return True, f"KYC {new_status}."
