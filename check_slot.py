import os
import datetime as dt
from zoneinfo import ZoneInfo
import requests

BASE = os.path.dirname(os.path.abspath(__file__))


def lade_env():
    pfad = os.path.join(BASE, ".env")
    if os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as f:
            for zeile in f:
                zeile = zeile.strip()
                if zeile and not zeile.startswith("#") and "=" in zeile:
                    k, v = zeile.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


lade_env()

TENANT_ID = os.environ["PLAYTOMIC_TENANT_ID"]
TOPIC = os.environ["NTFY_TOPIC"]

WUNSCH_UHRZEIT = "20:00:00"
DAUER_MIN = 90
TAGE_IM_VORAUS = 14
STATE_FILE = os.path.join(BASE, "gemeldet.txt")

HEADERS = {
    "accept": "*/*",
    "accept-language": "de,de-DE;q=0.9,en;q=0.8",
    "cookie": "pt_web_opened=1",
    "referer": "https://playtomic.com/clubs/padel-club-weinstrasse",
    "sec-ch-ua": '"Chromium";v="158", "Not.A/Brand";v="24", "Microsoft Edge";v="158"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36 Edg/158.0.0.0",
}


def ziel_montage():
    heute = dt.datetime.now(ZoneInfo("Europe/Berlin")).date()
    tage = [heute + dt.timedelta(days=i) for i in range(TAGE_IM_VORAUS + 1)]
    return [t for t in tage if t.weekday() == 0]


def slot_frei(tag):
    r = requests.get(
        "https://playtomic.com/api/clubs/availability",
        params={"tenant_id": TENANT_ID, "date": str(tag), "sport_id": "PADEL"},
        headers=HEADERS,
        timeout=30,
    )
    if not r.ok:
        raise SystemExit(f"{r.status_code}: {r.text[:500]}")
    for court in r.json():
        for slot in court.get("slots", []):
            if slot.get("start_time") == WUNSCH_UHRZEIT and slot.get("duration") == DAUER_MIN:
                return True
    return False


def gemeldet():
    try:
        with open(STATE_FILE) as f:
            return set(f.read().split())
    except FileNotFoundError:
        return set()


def push(text):
    r = requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=text.encode("utf-8"),
        headers={"Title": "Padel-Slot frei", "Click": "https://playtomic.com"},
        timeout=30,
    )
    r.raise_for_status()


def main():
    schon = gemeldet()
    for tag in ziel_montage():
        if str(tag) in schon:
            continue
        if slot_frei(tag):
            push(f"Montag {tag}, 20:00 Uhr, 90 Min, Padel Club Weinstraße. Jetzt buchen!")
            with open(STATE_FILE, "a") as f:
                f.write(f"{tag}\n")


if __name__ == "__main__":
    main()
