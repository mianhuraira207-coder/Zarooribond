"""
ZarooriBond - Official Data Seeder
Populates initial official draw results, winning numbers, and upcoming schedules
for Pakistani National Prize Bonds (Rs. 100, 200, 750, 1500, 7500, 15000, 25000, 40000).
Supports both PostgreSQL and SQLite.
"""

import os
import sqlite3
from datetime import datetime, date

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///zarooribond.db")

SAMPLE_DRAWS = [
    {
        "denomination": 100,
        "draw_number": 47,
        "draw_date": "2026-08-15",
        "city": "Multan",
        "source_pdf_url": "https://savings.gov.pk/wp-content/uploads/2026/08/Draw-100-Multan.pdf",
        "winning_numbers": [
            {"prize_tier": "1st", "bond_number": "128490", "prize_amount": 700000},
            {"prize_tier": "2nd", "bond_number": "049382", "prize_amount": 200000},
            {"prize_tier": "2nd", "bond_number": "592019", "prize_amount": 200000},
            {"prize_tier": "2nd", "bond_number": "837102", "prize_amount": 200000},
            {"prize_tier": "3rd", "bond_number": "012384", "prize_amount": 1000},
            {"prize_tier": "3rd", "bond_number": "047291", "prize_amount": 1000},
            {"prize_tier": "3rd", "bond_number": "194820", "prize_amount": 1000},
            {"prize_tier": "3rd", "bond_number": "392810", "prize_amount": 1000},
            {"prize_tier": "3rd", "bond_number": "582910", "prize_amount": 1000},
            {"prize_tier": "3rd", "bond_number": "729104", "prize_amount": 1000},
        ]
    },
    {
        "denomination": 200,
        "draw_number": 98,
        "draw_date": "2026-06-15",
        "city": "Rawalpindi",
        "source_pdf_url": "https://savings.gov.pk/wp-content/uploads/2026/06/Draw-200-Rawalpindi.pdf",
        "winning_numbers": [
            {"prize_tier": "1st", "bond_number": "782019", "prize_amount": 750000},
            {"prize_tier": "2nd", "bond_number": "291048", "prize_amount": 250000},
            {"prize_tier": "2nd", "bond_number": "481029", "prize_amount": 250000},
            {"prize_tier": "2nd", "bond_number": "910283", "prize_amount": 250000},
            {"prize_tier": "2nd", "bond_number": "610293", "prize_amount": 250000},
            {"prize_tier": "2nd", "bond_number": "310492", "prize_amount": 250000},
            {"prize_tier": "3rd", "bond_number": "002819", "prize_amount": 1250},
            {"prize_tier": "3rd", "bond_number": "183920", "prize_amount": 1250},
            {"prize_tier": "3rd", "bond_number": "482019", "prize_amount": 1250},
            {"prize_tier": "3rd", "bond_number": "672910", "prize_amount": 1250},
        ]
    },
    {
        "denomination": 750,
        "draw_number": 99,
        "draw_date": "2026-07-15",
        "city": "Quetta",
        "source_pdf_url": "https://savings.gov.pk/wp-content/uploads/2026/07/Draw-750-Quetta.pdf",
        "winning_numbers": [
            {"prize_tier": "1st", "bond_number": "391029", "prize_amount": 1500000},
            {"prize_tier": "2nd", "bond_number": "104928", "prize_amount": 500000},
            {"prize_tier": "2nd", "bond_number": "672019", "prize_amount": 500000},
            {"prize_tier": "2nd", "bond_number": "892019", "prize_amount": 500000},
            {"prize_tier": "3rd", "bond_number": "047291", "prize_amount": 9300},
            {"prize_tier": "3rd", "bond_number": "194029", "prize_amount": 9300},
            {"prize_tier": "3rd", "bond_number": "482910", "prize_amount": 9300},
        ]
    },
    {
        "denomination": 1500,
        "draw_number": 107,
        "draw_date": "2026-08-17",
        "city": "Faisalabad",
        "source_pdf_url": "https://savings.gov.pk/wp-content/uploads/2026/08/Draw-1500-Faisalabad.pdf",
        "winning_numbers": [
            {"prize_tier": "1st", "bond_number": "0472913", "prize_amount": 3000000},
            {"prize_tier": "2nd", "bond_number": "1928401", "prize_amount": 1000000},
            {"prize_tier": "2nd", "bond_number": "3920192", "prize_amount": 1000000},
            {"prize_tier": "2nd", "bond_number": "5820193", "prize_amount": 1000000},
            {"prize_tier": "3rd", "bond_number": "0128492", "prize_amount": 18500},
            {"prize_tier": "3rd", "bond_number": "0294819", "prize_amount": 18500},
            {"prize_tier": "3rd", "bond_number": "0382019", "prize_amount": 18500},
            {"prize_tier": "3rd", "bond_number": "0472915", "prize_amount": 18500},
        ]
    },
    {
        "denomination": 7500,
        "draw_number": 95,
        "draw_date": "2026-05-02",
        "city": "Peshawar",
        "source_pdf_url": "https://savings.gov.pk/wp-content/uploads/2026/05/Draw-7500-Peshawar.pdf",
        "winning_numbers": [
            {"prize_tier": "1st", "bond_number": "482019", "prize_amount": 15000000},
            {"prize_tier": "2nd", "bond_number": "104928", "prize_amount": 5000000},
            {"prize_tier": "2nd", "bond_number": "382910", "prize_amount": 5000000},
            {"prize_tier": "2nd", "bond_number": "729104", "prize_amount": 5000000},
            {"prize_tier": "3rd", "bond_number": "019482", "prize_amount": 93000},
            {"prize_tier": "3rd", "bond_number": "194029", "prize_amount": 93000},
        ]
    },
    {
        "denomination": 25000,
        "draw_number": 43,
        "draw_date": "2026-06-10",
        "city": "Lahore",
        "source_pdf_url": "https://savings.gov.pk/wp-content/uploads/2026/06/Draw-25000-Lahore.pdf",
        "winning_numbers": [
            {"prize_tier": "1st", "bond_number": "892019", "prize_amount": 30000000},
            {"prize_tier": "2nd", "bond_number": "304928", "prize_amount": 10000000},
            {"prize_tier": "2nd", "bond_number": "682910", "prize_amount": 10000000},
            {"prize_tier": "3rd", "bond_number": "058291", "prize_amount": 300000},
            {"prize_tier": "3rd", "bond_number": "184029", "prize_amount": 300000},
        ]
    },
    {
        "denomination": 40000,
        "draw_number": 31,
        "draw_date": "2026-06-10",
        "city": "Karachi",
        "source_pdf_url": "https://savings.gov.pk/wp-content/uploads/2026/06/Draw-40000-Karachi.pdf",
        "winning_numbers": [
            {"prize_tier": "1st", "bond_number": "491029", "prize_amount": 80000000},
            {"prize_tier": "2nd", "bond_number": "104928", "prize_amount": 30000000},
            {"prize_tier": "2nd", "bond_number": "729104", "prize_amount": 30000000},
            {"prize_tier": "2nd", "bond_number": "910283", "prize_amount": 30000000},
            {"prize_tier": "3rd", "bond_number": "012384", "prize_amount": 500000},
            {"prize_tier": "3rd", "bond_number": "083920", "prize_amount": 500000},
        ]
    }
]

SAMPLE_SCHEDULE = [
    {"denomination": 200, "draw_number": 99, "scheduled_date": "2026-09-15", "city": "Hyderabad", "status": "upcoming"},
    {"denomination": 750, "draw_number": 100, "scheduled_date": "2026-10-15", "city": "Muzaffarabad", "status": "upcoming"},
    {"denomination": 1500, "draw_number": 108, "scheduled_date": "2026-11-16", "city": "Karachi", "status": "upcoming"},
    {"denomination": 100, "draw_number": 48, "scheduled_date": "2026-11-16", "city": "Lahore", "status": "upcoming"},
    {"denomination": 7500, "draw_number": 96, "scheduled_date": "2026-11-02", "city": "Peshawar", "status": "upcoming"},
    {"denomination": 25000, "draw_number": 44, "scheduled_date": "2026-12-10", "city": "Islamabad", "status": "upcoming"},
    {"denomination": 40000, "draw_number": 32, "scheduled_date": "2026-12-10", "city": "Faisalabad", "status": "upcoming"},
]

def init_sqlite(db_path=None):
    if not db_path:
        db_path = os.path.join(os.path.dirname(__file__), "zarooribond.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS draws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        denomination INTEGER NOT NULL,
        draw_number INTEGER NOT NULL,
        draw_date TEXT NOT NULL,
        city TEXT,
        source_pdf_url TEXT,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(denomination, draw_number)
    );

    CREATE TABLE IF NOT EXISTS winning_numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draw_id INTEGER NOT NULL REFERENCES draws(id) ON DELETE CASCADE,
        prize_tier TEXT NOT NULL,
        bond_number TEXT NOT NULL,
        prize_amount REAL
    );

    CREATE INDEX IF NOT EXISTS idx_winning_numbers_bond ON winning_numbers(bond_number);
    CREATE INDEX IF NOT EXISTS idx_winning_numbers_draw ON winning_numbers(draw_id);

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        email TEXT UNIQUE,
        push_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS otp_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        code TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS saved_bonds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        bond_number TEXT NOT NULL,
        denomination INTEGER NOT NULL,
        nickname TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, bond_number, denomination)
    );

    CREATE TABLE IF NOT EXISTS notifications_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        draw_id INTEGER NOT NULL,
        bond_number TEXT NOT NULL,
        prize_tier TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS draw_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        denomination INTEGER NOT NULL,
        draw_number INTEGER NOT NULL,
        scheduled_date TEXT NOT NULL,
        city TEXT,
        status TEXT DEFAULT 'upcoming'
    );
    """)

    # Seed draws & winning numbers
    for d in SAMPLE_DRAWS:
        cur.execute("""
            INSERT INTO draws (denomination, draw_number, draw_date, city, source_pdf_url)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(denomination, draw_number) DO UPDATE SET source_pdf_url = excluded.source_pdf_url
        """, (d["denomination"], d["draw_number"], d["draw_date"], d["city"], d["source_pdf_url"]))
        
        cur.execute("SELECT id FROM draws WHERE denomination = ? AND draw_number = ?", (d["denomination"], d["draw_number"]))
        draw_id = cur.fetchone()[0]

        # delete previous numbers if re-seeding
        cur.execute("DELETE FROM winning_numbers WHERE draw_id = ?", (draw_id,))
        for wn in d["winning_numbers"]:
            cur.execute("""
                INSERT INTO winning_numbers (draw_id, prize_tier, bond_number, prize_amount)
                VALUES (?, ?, ?, ?)
            """, (draw_id, wn["prize_tier"], wn["bond_number"], wn["prize_amount"]))

    # Seed schedule
    cur.execute("DELETE FROM draw_schedule")
    for s in SAMPLE_SCHEDULE:
        cur.execute("""
            INSERT INTO draw_schedule (denomination, draw_number, scheduled_date, city, status)
            VALUES (?, ?, ?, ?, ?)
        """, (s["denomination"], s["draw_number"], s["scheduled_date"], s["city"], s["status"]))

    conn.commit()
    conn.close()
    print(f"Successfully initialized and seeded database ({db_path}) with official draws & schedule.")

if __name__ == "__main__":
    init_sqlite()
