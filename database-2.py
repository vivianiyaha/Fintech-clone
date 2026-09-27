"""
database.py
SQLite persistence layer for the exchange.

Tables:
    users            - accounts, hashed passwords, KYC tier, status
    kyc_records      - KYC submissions per user (BVN/NIN/ID/address doc refs)
    wallets          - per-user balances for NGN, BTC, ETH, USDT
    transactions     - unified ledger: deposits, withdrawals, trades
    aml_flags        - transactions flagged by rule engine for manual review
    audit_log        - admin/compliance actions (who did what, when)
    crypto_addresses - deposit addresses assigned per user per asset

NOTE ON PRODUCTION READINESS:
This uses SQLite for a fully runnable, zero-config demo. For production you would
swap this module for a managed Postgres/MySQL connection (e.g. via SQLAlchemy),
add row-level encryption for PII (BVN/NIN/ID numbers), and move secrets to a
vault instead of plaintext columns.
"""

import sqlite3
import os
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exchange.db")
_local = threading.local()


def get_conn():
    """Thread-local SQLite connection (Streamlit reruns on each interaction,
    so we keep one connection per thread instead of per call)."""
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA foreign_keys = ON")
    return _local.conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            kyc_tier INTEGER NOT NULL DEFAULT 0,
            is_admin INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',  -- active, suspended, frozen
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS kyc_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            tier_requested INTEGER NOT NULL,
            bvn TEXT,
            nin TEXT,
            id_type TEXT,
            id_number TEXT,
            address TEXT,
            is_pep INTEGER DEFAULT 0,
            sanctions_hit INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',  -- pending, approved, rejected
            reviewer_note TEXT,
            submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
            reviewed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS wallets (
            user_id INTEGER NOT NULL REFERENCES users(id),
            asset TEXT NOT NULL,  -- NGN, BTC, ETH, USDT
            balance REAL NOT NULL DEFAULT 0,
            locked REAL NOT NULL DEFAULT 0,  -- held pending withdrawal review
            PRIMARY KEY (user_id, asset)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            type TEXT NOT NULL,       -- deposit_ngn, withdraw_ngn, deposit_crypto,
                                       -- withdraw_crypto, trade_buy, trade_sell
            asset TEXT NOT NULL,
            amount REAL NOT NULL,
            fee REAL NOT NULL DEFAULT 0,
            counter_asset TEXT,        -- for trades: the asset on the other side
            counter_amount REAL,
            rate REAL,
            status TEXT NOT NULL DEFAULT 'completed',  -- pending, completed, flagged, rejected
            reference TEXT,
            external_address TEXT,     -- withdrawal destination / deposit source
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS aml_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL REFERENCES transactions(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            rule_triggered TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',  -- low, medium, high
            status TEXT NOT NULL DEFAULT 'open',       -- open, cleared, escalated
            note TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT,
            details TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS crypto_addresses (
            user_id INTEGER NOT NULL REFERENCES users(id),
            asset TEXT NOT NULL,
            address TEXT NOT NULL,
            PRIMARY KEY (user_id, asset)
        );
        """
    )
    conn.commit()


def seed_admin():
    """Create a default admin/compliance officer account if none exists."""
    from auth import hash_password  # local import to avoid circular import

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1")
    if cur.fetchone():
        return
    cur.execute(
        """INSERT INTO users (full_name, email, phone, password_hash, kyc_tier, is_admin, status)
           VALUES (?, ?, ?, ?, ?, 1, 'active')""",
        ("Compliance Admin", "admin@exchange.local", "+2340000000000",
         hash_password("Admin123!"), 3),
    )
    conn.commit()
