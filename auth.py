"""
auth.py
Account registration, login, and password handling.
"""

import re
import bcrypt
from database import get_conn

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?\d{10,14}$")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def password_strength_ok(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password needs at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password needs at least one number."
    return True, ""


def register_user(full_name: str, email: str, phone: str, password: str) -> tuple[bool, str]:
    email = email.strip().lower()
    phone = phone.strip()

    if not full_name.strip():
        return False, "Full name is required."
    if not EMAIL_RE.match(email):
        return False, "Enter a valid email address."
    if not PHONE_RE.match(phone):
        return False, "Enter a valid phone number (10-14 digits, e.g. +2348012345678)."
    ok, msg = password_strength_ok(password)
    if not ok:
        return False, msg

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = ? OR phone = ?", (email, phone))
    if cur.fetchone():
        return False, "An account with this email or phone already exists."

    cur.execute(
        """INSERT INTO users (full_name, email, phone, password_hash, kyc_tier, status)
           VALUES (?, ?, ?, ?, 0, 'active')""",
        (full_name.strip(), email, phone, hash_password(password)),
    )
    user_id = cur.lastrowid

    # Initialize a zero-balance wallet row for every supported asset.
    for asset in ("NGN", "BTC", "ETH", "USDT"):
        cur.execute(
            "INSERT INTO wallets (user_id, asset, balance, locked) VALUES (?, ?, 0, 0)",
            (user_id, asset),
        )
    conn.commit()
    return True, "Account created. Please log in."


def login_user(email_or_phone: str, password: str):
    """Returns the user row (sqlite3.Row) on success, or None."""
    identifier = email_or_phone.strip().lower()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE lower(email) = ? OR phone = ?",
        (identifier, email_or_phone.strip()),
    )
    user = cur.fetchone()
    if not user:
        return None
    if user["status"] != "active":
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def get_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cur.fetchone()
