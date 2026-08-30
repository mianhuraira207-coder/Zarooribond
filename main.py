"""
ZarooriBond - Official National Prize Bond Backend API
------------------------------------------------------
Supports PostgreSQL and SQLite out of the box.
Features:
- Single, Batch, and Range bond verification
- Official Draw explorer & Prize tier breakdown
- Official Schedule & countdowns
- Portfolio management & automatic win scanning
- Phone OTP & JWT session auth
"""

import os
import sqlite3
from datetime import date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///zarooribond.db")
USE_POSTGRES = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
import jwt as pyjwt
try:
    import auth as auth_module
except ImportError:
    from backend import auth as auth_module

app = FastAPI(
    title="ZarooriBond - Official Prize Bond Tracker API",
    description="Official Pakistan National Prize Bond Results, Verification & Tracking API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "zarooribond.db")


class DBConnection:
    def __init__(self):
        self.use_postgres = USE_POSTGRES
        self.conn = None

    def __enter__(self):
        if self.use_postgres:
            self.conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            self.conn = sqlite3.connect(DB_SQLITE_PATH)
            self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            self.conn.close()

    def query_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        if not self.use_postgres:
            # Replace %s with ? for sqlite
            query = query.replace("%s", "?")
        cur.execute(query, params)
        rows = cur.fetchall()
        if self.use_postgres:
            return [dict(row) for row in rows]
        else:
            return [dict(row) for row in rows]

    def query_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        if not self.use_postgres:
            query = query.replace("%s", "?")
        cur.execute(query, params)
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        cur = self.conn.cursor()
        if not self.use_postgres:
            query = query.replace("%s", "?")
            # SQLite does not always support RETURNING directly in old builds, handle safely
            cur.execute(query, params)
            return cur.lastrowid
        else:
            cur.execute(query, params)
            row = cur.fetchone()
            return row["id"] if row and "id" in row else 1

    def execute(self, query: str, params: tuple = ()):
        cur = self.conn.cursor()
        if not self.use_postgres:
            query = query.replace("%s", "?")
        cur.execute(query, params)


# Ensure database tables exist if on SQLite
def init_db():
    if not USE_POSTGRES:
        try:
            from seed_data import init_sqlite
        except ImportError:
            from backend.seed_data import init_sqlite
        init_sqlite(DB_SQLITE_PATH)


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- Schemas ----------

class BatchSearchRequest(BaseModel):
    bond_numbers: List[str] = Field(..., min_items=1, max_items=200)
    denomination: Optional[int] = None


class SaveBondRequest(BaseModel):
    bond_number: str
    denomination: int
    nickname: Optional[str] = None


class RequestOtpRequest(BaseModel):
    phone: str


class VerifyOtpRequest(BaseModel):
    phone: str
    code: str


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = auth_module.decode_jwt(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please sign in again")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session token")
    return payload


# ---------- Core: Search APIs ----------

@app.get("/api/search")
def search_bond(
    bond_number: str = Query(..., min_length=1, max_length=20),
    denomination: Optional[int] = None,
):
    """
    Search a single bond number across all draws.
    """
    clean_number = bond_number.strip().zfill(6)
    with DBConnection() as db:
        query = """
            SELECT
                d.id AS draw_id, d.denomination, d.draw_number, d.draw_date, d.city,
                d.source_pdf_url, wn.prize_tier, wn.prize_amount, wn.bond_number
            FROM winning_numbers wn
            JOIN draws d ON d.id = wn.draw_id
            WHERE (wn.bond_number = %s OR wn.bond_number = %s)
        """
        params = [bond_number.strip(), clean_number]
        if denomination:
            query += " AND d.denomination = %s"
            params.append(denomination)
        query += " ORDER BY d.draw_date DESC"

        matches = db.query_all(query, tuple(params))

    return {
        "bond_number": bond_number.strip(),
        "won": len(matches) > 0,
        "total_wins": len(matches),
        "total_prize": sum(m.get("prize_amount", 0) or 0 for m in matches),
        "matches": matches,
    }


@app.post("/api/search/batch")
def batch_search(req: BatchSearchRequest):
    """
    Search multiple bond numbers at once (up to 200).
    """
    cleaned_numbers = [n.strip() for n in req.bond_numbers if n.strip()]
    if not cleaned_numbers:
        raise HTTPException(status_code=400, detail="No valid bond numbers provided")

    results = []
    total_winnings = 0
    total_winning_bonds = 0

    with DBConnection() as db:
        for num in cleaned_numbers:
            clean_padded = num.zfill(6)
            query = """
                SELECT
                    d.id AS draw_id, d.denomination, d.draw_number, d.draw_date, d.city,
                    d.source_pdf_url, wn.prize_tier, wn.prize_amount, wn.bond_number
                FROM winning_numbers wn
                JOIN draws d ON d.id = wn.draw_id
                WHERE (wn.bond_number = %s OR wn.bond_number = %s)
            """
            params = [num, clean_padded]
            if req.denomination:
                query += " AND d.denomination = %s"
                params.append(req.denomination)
            query += " ORDER BY d.draw_date DESC"

            matches = db.query_all(query, tuple(params))
            won = len(matches) > 0
            if won:
                total_winning_bonds += 1
                total_winnings += sum(m.get("prize_amount", 0) or 0 for m in matches)

            results.append({
                "bond_number": num,
                "won": won,
                "matches": matches
            })

    return {
        "searched_count": len(cleaned_numbers),
        "winning_bonds_count": total_winning_bonds,
        "total_prize_amount": total_winnings,
        "results": results
    }


@app.get("/api/search/range")
def search_range(
    start_number: int = Query(..., ge=0),
    end_number: int = Query(..., ge=0),
    denomination: Optional[int] = None,
    pad_zeros: bool = True
):
    """
    Search a sequence / series range of bond numbers (e.g. 0472900 to 0472950).
    Max range 250 numbers at a time for performance.
    """
    if start_number > end_number:
        raise HTTPException(status_code=400, detail="start_number cannot be greater than end_number")
    
    count = end_number - start_number + 1
    if count > 250:
        raise HTTPException(status_code=400, detail="Range cannot exceed 250 numbers at a time")

    numbers_to_check = [
        str(n).zfill(6) if pad_zeros else str(n)
        for n in range(start_number, end_number + 1)
    ]

    return batch_search(BatchSearchRequest(bond_numbers=numbers_to_check, denomination=denomination))


# ---------- Draws & Results APIs ----------

@app.get("/api/draws")
def list_draws(denomination: Optional[int] = None, limit: int = 50):
    with DBConnection() as db:
        query = "SELECT * FROM draws"
        params = []
        if denomination:
            query += " WHERE denomination = %s"
            params.append(denomination)
        query += " ORDER BY draw_date DESC LIMIT %s"
        params.append(limit)
        return db.query_all(query, tuple(params))


@app.get("/api/draws/{draw_id}/results")
def draw_results(draw_id: int, prize_tier: Optional[str] = None):
    with DBConnection() as db:
        draw = db.query_one("SELECT * FROM draws WHERE id = %s", (draw_id,))
        if not draw:
            raise HTTPException(status_code=404, detail="Draw not found")

        query = "SELECT * FROM winning_numbers WHERE draw_id = %s"
        params = [draw_id]
        if prize_tier:
            query += " AND prize_tier = %s"
            params.append(prize_tier)
        query += " ORDER BY id ASC"
        rows = db.query_all(query, tuple(params))

        return {
            "draw": draw,
            "total_winning_numbers": len(rows),
            "winning_numbers": rows
        }


@app.get("/api/schedule")
def upcoming_schedule(denomination: Optional[int] = None):
    with DBConnection() as db:
        query = "SELECT * FROM draw_schedule"
        params = []
        if denomination:
            query += " WHERE denomination = %s"
            params.append(denomination)
        query += " ORDER BY scheduled_date ASC"
        return db.query_all(query, tuple(params))


@app.get("/api/stats")
def platform_stats():
    with DBConnection() as db:
        draws_count = db.query_one("SELECT COUNT(*) AS c FROM draws")
        numbers_count = db.query_one("SELECT COUNT(*) AS c, SUM(prize_amount) AS total_prize FROM winning_numbers")
        upcoming_count = db.query_one("SELECT COUNT(*) AS c FROM draw_schedule WHERE status = 'upcoming'")

        return {
            "total_draws_indexed": draws_count.get("c", 0) if draws_count else 0,
            "total_winning_numbers": numbers_count.get("c", 0) if numbers_count else 0,
            "total_prize_value_indexed": numbers_count.get("total_prize", 0) or 0 if numbers_count else 0,
            "upcoming_draws": upcoming_count.get("c", 0) if upcoming_count else 0,
            "supported_denominations": [100, 200, 750, 1500, 7500, 15000, 25000, 40000]
        }


# ---------- Auth & Saved Bonds ----------

@app.post("/api/auth/request-otp")
def request_otp(req: RequestOtpRequest):
    phone = req.phone.strip()
    with DBConnection() as db:
        code = auth_module.generate_otp_code()
        auth_module.send_otp_sms(phone, code)
        db.execute(
            "INSERT INTO otp_codes (phone, code, expires_at) VALUES (%s, %s, datetime('now', '+5 minutes'))"
            if not USE_POSTGRES else
            "INSERT INTO otp_codes (phone, code, expires_at) VALUES (%s, %s, NOW() + INTERVAL '5 minutes')",
            (phone, code)
        )
        return {"status": "sent", "phone": phone, "dev_hint": f"Development OTP is {code}"}


@app.post("/api/auth/verify-otp")
def verify_otp(req: VerifyOtpRequest):
    phone = req.phone.strip()
    code = req.code.strip()
    with DBConnection() as db:
        otp_row = db.query_one(
            """
            SELECT id FROM otp_codes
            WHERE phone = %s AND code = %s AND used = 0
            ORDER BY created_at DESC LIMIT 1
            """ if not USE_POSTGRES else
            """
            SELECT id FROM otp_codes
            WHERE phone = %s AND code = %s AND used = FALSE AND expires_at > NOW()
            ORDER BY created_at DESC LIMIT 1
            """,
            (phone, code)
        )
        if not otp_row:
            raise HTTPException(status_code=400, detail="Invalid or expired code")

        # Mark used
        db.execute(
            "UPDATE otp_codes SET used = 1 WHERE id = %s" if not USE_POSTGRES else
            "UPDATE otp_codes SET used = TRUE WHERE id = %s",
            (otp_row["id"],)
        )

        # Get or create user
        user = db.query_one("SELECT id, phone FROM users WHERE phone = %s", (phone,))
        if not user:
            user_id = db.execute_insert("INSERT INTO users (phone) VALUES (%s)", (phone,))
            user = {"id": user_id, "phone": phone}

        token = auth_module.issue_jwt(user["id"], user["phone"])
        return {"token": token, "user": user}


@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.post("/api/saved-bonds")
def save_bond(req: SaveBondRequest, current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["sub"])
    bond_num = req.bond_number.strip()
    with DBConnection() as db:
        existing = db.query_one(
            "SELECT id FROM saved_bonds WHERE user_id = %s AND bond_number = %s AND denomination = %s",
            (user_id, bond_num, req.denomination)
        )
        if existing:
            return {"status": "already_saved", "id": existing["id"]}

        bond_id = db.execute_insert(
            "INSERT INTO saved_bonds (user_id, bond_number, denomination, nickname) VALUES (%s, %s, %s, %s)",
            (user_id, bond_num, req.denomination, req.nickname)
        )
        return {"status": "saved", "id": bond_id, "bond_number": bond_num, "denomination": req.denomination}


@app.get("/api/saved-bonds")
def get_saved_bonds(current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with DBConnection() as db:
        return db.query_all("SELECT * FROM saved_bonds WHERE user_id = %s ORDER BY created_at DESC", (user_id,))


@app.delete("/api/saved-bonds/{bond_id}")
def delete_saved_bond(bond_id: int, current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with DBConnection() as db:
        db.execute("DELETE FROM saved_bonds WHERE id = %s AND user_id = %s", (bond_id, user_id))
        return {"status": "deleted"}


@app.get("/api/saved-bonds/check-all")
def check_all_saved_bonds(current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with DBConnection() as db:
        bonds = db.query_all("SELECT * FROM saved_bonds WHERE user_id = %s", (user_id,))
        if not bonds:
            return {"total_saved": 0, "winning_bonds": 0, "total_winnings": 0, "results": []}

        results = []
        total_winnings = 0
        winning_count = 0

        for b in bonds:
            num = b["bond_number"]
            denom = b["denomination"]
            query = """
                SELECT
                    d.denomination, d.draw_number, d.draw_date, d.city,
                    d.source_pdf_url, wn.prize_tier, wn.prize_amount
                FROM winning_numbers wn
                JOIN draws d ON d.id = wn.draw_id
                WHERE (wn.bond_number = %s OR wn.bond_number = %s) AND d.denomination = %s
                ORDER BY d.draw_date DESC
            """
            matches = db.query_all(query, (num, num.zfill(6), denom))
            won = len(matches) > 0
            if won:
                winning_count += 1
                total_winnings += sum(m.get("prize_amount", 0) or 0 for m in matches)

            results.append({
                "id": b["id"],
                "bond_number": num,
                "denomination": denom,
                "nickname": b.get("nickname"),
                "won": won,
                "matches": matches
            })

        return {
            "total_saved": len(bonds),
            "winning_bonds": winning_count,
            "total_winnings": total_winnings,
            "results": results
        }


from fastapi.responses import PlainTextResponse, Response

@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots():
    return "User-agent: *\nAllow: /\nSitemap: https://zarooribond.pk/sitemap.xml\n"

@app.get("/sitemap.xml")
def get_sitemap():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://zarooribond.pk/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
  <url><loc>https://zarooribond.pk/#check</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://zarooribond.pk/#draws</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://zarooribond.pk/#schedule</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>https://zarooribond.pk/#guide</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>
</urlset>"""
    return Response(content=content, media_type="application/xml")

@app.get("/health")
def health():
    return {"status": "ok", "service": "ZarooriBond Official Prize Bond Tracker", "db_mode": "postgres" if USE_POSTGRES else "sqlite"}
