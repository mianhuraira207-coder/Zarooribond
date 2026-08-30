"""
ZarooriBond Auth Module
------------------------
Phone-number OTP sign-in, the standard pattern for Pakistani apps.

Flow:
  1. POST /api/auth/request-otp  { phone }       -> sends a 6-digit code
  2. POST /api/auth/verify-otp   { phone, code } -> returns a JWT + user

The JWT is then sent as `Authorization: Bearer <token>` on requests that
need to know who the user is (e.g. saving a bond).

SMS SENDING: this file generates and stores the code but does not send
an actual SMS — that requires a provider account (e.g. Twilio, or a
Pakistani SMS gateway like Telesign/Jazz/Zong business SMS APIs). Wire
your provider's API call into `send_otp_sms()` below.

Install:
    pip install pyjwt --break-system-packages
"""

import os
import random
import string
from datetime import datetime, timedelta, timezone

import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30
OTP_EXPIRY_MINUTES = 5


def generate_otp_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def send_otp_sms(phone: str, code: str):
    """
    Send the OTP code via SMS. Replace this with a real provider call,
    e.g.:

        import requests
        requests.post("https://api.your-sms-provider.com/send", json={
            "to": phone,
            "message": f"Your ZarooriBond code is {code}. Valid for 5 minutes.",
        })

    For local development, this just prints the code to the console so
    you can test the flow without a real SMS provider set up yet.
    """
    print(f"[DEV] OTP for {phone}: {code}  (wire up a real SMS provider before shipping)")


def create_otp(conn, phone: str) -> str:
    """Generate a code, store it, and 'send' it. Returns the code (dev only — don't return this to the client in production)."""
    code = generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO otp_codes (phone, code, expires_at) VALUES (%s, %s, %s)",
            (phone, code, expires_at),
        )
        conn.commit()
    send_otp_sms(phone, code)
    return code


def verify_otp(conn, phone: str, code: str) -> bool:
    """Check a submitted code against the latest unused, unexpired OTP for this phone."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM otp_codes
            WHERE phone = %s AND code = %s AND used = FALSE AND expires_at > NOW()
            ORDER BY created_at DESC LIMIT 1
            """,
            (phone, code),
        )
        row = cur.fetchone()
        if not row:
            return False
        otp_id = row[0] if not isinstance(row, dict) else row["id"]
        cur.execute("UPDATE otp_codes SET used = TRUE WHERE id = %s", (otp_id,))
        conn.commit()
        return True


def issue_jwt(user_id: int, phone: str) -> str:
    payload = {
        "sub": str(user_id),
        "phone": phone,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Raises jwt.InvalidTokenError / jwt.ExpiredSignatureError on failure."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
