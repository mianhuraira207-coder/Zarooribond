"""
ZarooriBond Push Notifications
--------------------------------
Sends push notifications via Expo's push service. Since the mobile app
is built with Expo, this is the simplest path — no separate Firebase
setup needed for the starter (Expo handles delivery to both iOS and
Android under the hood).

Install:
    pip install requests --break-system-packages
"""

import requests

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_push_notification(push_token: str, title: str, body: str, data: dict = None):
    """
    Send a single push notification to an Expo push token
    (looks like "ExponentPushToken[xxxxxxxx]").
    """
    if not push_token or not push_token.startswith("ExponentPushToken"):
        print(f"Skipping push — not a valid Expo push token: {push_token}")
        return

    message = {
        "to": push_token,
        "sound": "default",
        "title": title,
        "body": body,
        "data": data or {},
    }

    try:
        resp = requests.post(
            EXPO_PUSH_URL,
            json=message,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"Push notification failed for {push_token}: {e}")
        return None


def notify_saved_bond_winners(conn, draw_id: int):
    """
    After a draw's winning numbers are imported, check which users have
    saved a matching bond number and push-notify each of them. Call this
    from scraper.py's import_draw() right after inserting winning_numbers.
    Also logs to notifications_log so we never double-notify the same
    user for the same draw + bond number.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT
                u.id AS user_id, u.push_token,
                sb.bond_number, wn.prize_tier, wn.prize_amount,
                d.denomination, d.draw_number
            FROM winning_numbers wn
            JOIN draws d ON d.id = wn.draw_id
            JOIN saved_bonds sb
                ON sb.bond_number = wn.bond_number
                AND sb.denomination = d.denomination
            JOIN users u ON u.id = sb.user_id
            WHERE wn.draw_id = %s
              AND u.push_token IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM notifications_log nl
                  WHERE nl.user_id = u.id
                    AND nl.draw_id = wn.draw_id
                    AND nl.bond_number = wn.bond_number
              )
            """,
            (draw_id,),
        )
        matches = cur.fetchall()

        for row in matches:
            user_id, push_token, bond_number, prize_tier, prize_amount, denomination, draw_number = row

            send_push_notification(
                push_token,
                title="🎉 Your bond won!",
                body=f"Bond {bond_number} (Rs. {denomination}) won the {prize_tier} prize in Draw #{draw_number}.",
                data={"bond_number": bond_number, "draw_id": draw_id},
            )

            cur.execute(
                """
                INSERT INTO notifications_log (user_id, draw_id, bond_number, prize_tier)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, draw_id, bond_number, prize_tier),
            )

        conn.commit()
        print(f"Notified {len(matches)} saved-bond match(es) for draw {draw_id}")
