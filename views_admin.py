import streamlit as st
from database import get_conn
from kyc import pending_kyc_queue, review_kyc


def render_admin(user):
    st.markdown("## 🛡️ Compliance Dashboard")
    st.caption("Admin/compliance-officer view: KYC review queue, AML flags, audit log.")

    tab_kyc, tab_aml, tab_audit, tab_users = st.tabs(
        ["KYC Queue", "AML Flags", "Audit Log", "Users"]
    )

    with tab_kyc:
        queue = pending_kyc_queue()
        if not queue:
            st.caption("No pending KYC submissions.")
        for rec in queue:
            with st.expander(f"{rec['full_name']} — Tier {rec['tier_requested']} "
                              f"({rec['submitted_at']})"):
                st.write(f"**Email:** {rec['email']}")
                if rec["bvn"]:
                    st.write(f"**BVN:** {rec['bvn']}")
                if rec["nin"]:
                    st.write(f"**NIN:** {rec['nin']}")
                if rec["id_type"]:
                    st.write(f"**ID:** {rec['id_type']} — {rec['id_number']}")
                if rec["address"]:
                    st.write(f"**Address:** {rec['address']}")
                if rec["is_pep"]:
                    st.warning("Flagged as PEP.")
                if rec["sanctions_hit"]:
                    st.error("⚠️ Sanctions/watchlist name match.")
                note = st.text_input("Reviewer note", key=f"note_{rec['id']}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Approve", key=f"approve_{rec['id']}", use_container_width=True):
                        review_kyc(rec["id"], True, note, user["email"])
                        st.rerun()
                with c2:
                    if st.button("Reject", key=f"reject_{rec['id']}", use_container_width=True):
                        review_kyc(rec["id"], False, note, user["email"])
                        st.rerun()

    with tab_aml:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT aml_flags.*, users.full_name, users.email, transactions.type,
                      transactions.asset, transactions.amount, transactions.created_at as txn_time
               FROM aml_flags
               JOIN users ON users.id = aml_flags.user_id
               JOIN transactions ON transactions.id = aml_flags.transaction_id
               WHERE aml_flags.status = 'open'
               ORDER BY aml_flags.created_at DESC"""
        )
        flags = cur.fetchall()
        if not flags:
            st.caption("No open AML flags.")
        for f in flags:
            severity_color = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(f["severity"], "🟠")
            with st.expander(f"{severity_color} {f['rule_triggered']} — {f['full_name']} "
                              f"({f['type']} {f['amount']} {f['asset']})"):
                st.write(f"**User:** {f['full_name']} ({f['email']})")
                st.write(f"**Rule:** {f['rule_triggered']}  ·  **Severity:** {f['severity']}")
                st.write(f"**Note:** {f['note']}")
                st.write(f"**Transaction time:** {f['txn_time']}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Clear flag", key=f"clear_{f['id']}", use_container_width=True):
                        cur.execute("UPDATE aml_flags SET status='cleared' WHERE id=?", (f["id"],))
                        cur.execute("UPDATE transactions SET status='completed' WHERE id=?",
                                    (f["transaction_id"],))
                        cur.execute(
                            "INSERT INTO audit_log (actor, action, target) VALUES (?, ?, ?)",
                            (user["email"], "aml_flag_cleared", f"txn:{f['transaction_id']}"),
                        )
                        conn.commit()
                        st.rerun()
                with c2:
                    if st.button("Escalate / reject txn", key=f"escalate_{f['id']}", use_container_width=True):
                        cur.execute("UPDATE aml_flags SET status='escalated' WHERE id=?", (f["id"],))
                        cur.execute("UPDATE transactions SET status='rejected' WHERE id=?",
                                    (f["transaction_id"],))
                        cur.execute(
                            "INSERT INTO audit_log (actor, action, target) VALUES (?, ?, ?)",
                            (user["email"], "aml_flag_escalated", f"txn:{f['transaction_id']}"),
                        )
                        conn.commit()
                        st.rerun()

    with tab_audit:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 100")
        rows = cur.fetchall()
        if not rows:
            st.caption("No audit entries yet.")
        for r in rows:
            st.markdown(f"`{r['created_at']}` **{r['actor']}** — {r['action']} "
                        f"({r['target'] or ''}) {('— ' + r['details']) if r['details'] else ''}")

    with tab_users:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, full_name, email, kyc_tier, status FROM users ORDER BY created_at DESC")
        rows = cur.fetchall()
        for r in rows:
            st.markdown(f"**{r['full_name']}** ({r['email']}) — Tier {r['kyc_tier']} — {r['status']}")
