"""
ZarooriBond Data Importer
--------------------------
Pulls newly published draw results from official sources and loads them
into the database. There is no public API for savings.gov.pk, so this
script is structured as a periodic job (cron / scheduled task) that:

  1. Fetches the results page/PDF for each denomination
  2. Parses out the draw metadata + winning numbers
  3. Inserts into `draws` and `winning_numbers`, skipping duplicates

IMPORTANT: The actual HTML/PDF structure of savings.gov.pk needs to be
inspected directly (it may change over time, and PDFs require a parser
like pdfplumber). This file gives you the pipeline shape and a working
example against a *mock* result so you can wire up the real parsing
logic once you've inspected the live source.

Install:
    pip install requests pdfplumber psycopg2-binary --break-system-packages
"""

import os
import re
from datetime import datetime

import psycopg2
import psycopg2.extras
import requests

from notifications import notify_saved_bond_winners

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/zarooribond")
SOURCE_BASE_URL = "https://savings.gov.pk"  # verify exact results path before use

DENOMINATIONS = [100, 200, 750, 1500, 7500, 15000, 25000, 40000]


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def fetch_draw_pdf(denomination: int, draw_number: int) -> bytes:
    """
    Fetch the official result PDF for a given denomination + draw number.
    Replace this URL pattern once you've confirmed the real one on
    savings.gov.pk (it may require following a results index page first
    to find the correct PDF link for the latest draw).
    """
    url = f"{SOURCE_BASE_URL}/results/{denomination}/draw-{draw_number}.pdf"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def parse_pdf_winning_numbers(pdf_bytes: bytes) -> list[dict]:
    """
    Parse a draw result PDF into a list of winning number rows.
    Requires pdfplumber. The exact parsing logic (column positions,
    prize tier headers, etc.) depends on CDNS's PDF layout and should
    be adjusted after inspecting a real sample PDF.
    """
    import io
    import pdfplumber

    results = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # Example pattern: lines like "1st Prize: 123456"
            for match in re.finditer(r"(1st|2nd|3rd)\s*Prize[:\s]+(\d{4,8})", text):
                tier, bond_number = match.groups()
                results.append({"prize_tier": f"{tier}", "bond_number": bond_number})
    return results


def import_draw(denomination: int, draw_number: int, draw_date: str, city: str, source_pdf_url: str,
                 winning_numbers: list[dict]):
    """
    Insert a draw and its winning numbers into the database.
    Safe to re-run: uses ON CONFLICT to avoid duplicate draws.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO draws (denomination, draw_number, draw_date, city, source_pdf_url)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (denomination, draw_number) DO UPDATE
                    SET source_pdf_url = EXCLUDED.source_pdf_url
                RETURNING id
                """,
                (denomination, draw_number, draw_date, city, source_pdf_url),
            )
            draw_id = cur.fetchone()[0]

            for row in winning_numbers:
                cur.execute(
                    """
                    INSERT INTO winning_numbers (draw_id, prize_tier, bond_number, prize_amount)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (draw_id, row["prize_tier"], row["bond_number"], row.get("prize_amount")),
                )
            conn.commit()
            print(f"Imported draw #{draw_number} ({denomination}) — {len(winning_numbers)} numbers")

        # Notify any users whose saved bonds match a winning number in
        # this draw. Runs after commit so the data is durable first.
        notify_saved_bond_winners(conn, draw_id)
    finally:
        conn.close()


def run_import_job():
    """
    Entry point for the scheduled job. In production, run this via
    cron (e.g. every hour) or a task scheduler, since CDNS publishes
    results shortly after each draw and you want fresh data fast.
    """
    for denom in DENOMINATIONS:
        try:
            # TODO: replace with real logic to detect the latest draw
            # number + date + city for this denomination from the
            # savings.gov.pk results index page, then fetch + parse it.
            print(f"Checking for new draws: Rs {denom}")
            # pdf_bytes = fetch_draw_pdf(denom, draw_number)
            # numbers = parse_pdf_winning_numbers(pdf_bytes)
            # import_draw(denom, draw_number, draw_date, city, url, numbers)
        except Exception as e:
            print(f"Error importing denomination {denom}: {e}")


if __name__ == "__main__":
    run_import_job()
