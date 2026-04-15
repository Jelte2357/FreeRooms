import FreeRoomICS
from icalendar import Calendar, Component
from flask import Flask, request, send_file, render_template
import requests
from io import BytesIO
import traceback
import threading
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================

JSON_FILENAME = "Rooms.json"
CACHE_SECONDS = 900  # 15 minutes

# =========================
# STATE (in-memory only)
# =========================

app = Flask(__name__)

cal = None
last_update = None
update_lock = threading.Lock()


# =========================
# UTILITIES
# =========================


def alert_via_HA(title: str, message: str, url: str = "https://home-assistant.jelte2357.nl/api/webhook/ntfy", _headers: dict = {"content-type":"application/x-www-form-urlencoded"}) -> None:
    try:
        requests.post(url, data={"title": title, "message": message}, headers=_headers, timeout=10)
    except Exception as e:
        print(f"Error sending alert: {e}")

def update_calendar():
    global cal, last_update

    free_rooms_dict, timeslots = FreeRoomICS.cal_find_freerooms(
        JSON_FILENAME,
        False
    )

    cal = FreeRoomICS.freerooms_to_ics(
        free_rooms_dict,
        timeslots
    )

    last_update = datetime.now()

def should_refresh():
    global last_update

    if last_update is None:
        return True

    return (
        datetime.now() - last_update
        > timedelta(seconds=CACHE_SECONDS)
    )

# =========================
# ROUTES
# =========================

@app.route("/freerooms", methods=["GET"])
def freerooms():
    global cal

    try:
        if should_refresh():
            with update_lock: # Lock updating
                if should_refresh():
                    update_calendar()

        return send_file(
            BytesIO(cal.to_ical()), # type: ignore
            mimetype="text/calendar",
            as_attachment=True,
            download_name="freerooms.ics",
        )

    except Exception as e:
        traceback.print_exc()

        alert_via_HA(
            "Error in /freerooms endpoint",
            str(e) + "\n" + traceback.format_exc()
        )

        # Return proper HTTP error (no templates)
        return (
            "Internal Server Error\n\n"
            + str(e),
            500,
            {"Content-Type": "text/plain"}
        )
        
# =========================
# MAIN
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)