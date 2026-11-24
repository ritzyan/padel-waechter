import os
import sys
import datetime as dt
from zoneinfo import ZoneInfo
import requests

import padel_config as pc

pc.lade_env()

TENANT_ID = os.environ["PLAYTOMIC_TENANT_ID"]
TOPIC = os.environ["NTFY_TOPIC"]

STATE_FILE = os.path.join(pc.BASE, "gemeldet.txt")
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

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


def jetzt():
    return dt.datetime.now(ZoneInfo("Europe/Berlin"))


def ziel_tage(cfg):
    heute = jetzt().date()
    tage = [heute + dt.timedelta(days=i) for i in range(cfg["tage_im_voraus"] + 1)]
    return [t for t in tage if t.weekday() in cfg["wochentage"]]


def freie_startzeiten(tag, cfg):
    """Gibt die passenden freien Startzeiten (HH:MM) für einen Tag zurück."""
    r = requests.get(
        "https://playtomic.com/api/clubs/availability",
        params={"tenant_id": TENANT_ID, "date": str(tag), "sport_id": "PADEL"},
        headers=HEADERS,
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Playtomic {r.status_code}")
    treffer = set()
    for court in r.json():
        for slot in court.get("slots", []):
            zeit = (slot.get("start_time") or "")[:5]
            if slot.get("duration") == cfg["dauer_min"] and cfg["start_von"] <= zeit <= cfg["start_bis"]:
                treffer.add(zeit)
    return sorted(treffer)


def gemeldet():
    try:
        with open(STATE_FILE) as f:
            return set(f.read().split("\n"))
    except FileNotFoundError:
        return set()


def push(text):
    r = requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=text.encode("utf-8"),
        headers={"Title": "Padel-Slot frei", "Click": "https://playtomic.com/clubs/padel-club-weinstrasse"},
        timeout=30,
    )
    r.raise_for_status()


def pruefe(cfg):
    """Prüft alle Zieltage, meldet neue Treffer und gibt sie zurück."""
    schon = gemeldet()
    neu = []
    for tag in ziel_tage(cfg):
        zeiten = [z for z in freie_startzeiten(tag, cfg) if f"{tag} {z}" not in schon]
        if not zeiten:
            continue
        text = (
            f"{WOCHENTAGE[tag.weekday()]} {tag.strftime('%d.%m.')}: frei um "
            f"{', '.join(zeiten)} Uhr ({cfg['dauer_min']} Min), Padel Club Weinstraße. Jetzt buchen!"
        )
        push(text)
        with open(STATE_FILE, "a") as f:
            for z in zeiten:
                f.write(f"{tag} {z}\n")
        neu.extend(f"{tag.strftime('%d.%m.')} {z}" for z in zeiten)
    return neu


def main():
    cfg = pc.lade_config()
    status = {"letzter_lauf": jetzt().strftime("%d.%m.%Y %H:%M:%S")}
    if not cfg["aktiv"]:
        status["ergebnis"] = "pausiert"
        pc.speichere_status(status)
        return 0
    try:
        neu = pruefe(cfg)
    except Exception as e:  # Netzwerkfehler usw. sollen den Cron-Job nicht zerlegen
        status["ergebnis"] = f"Fehler: {e}"
        pc.speichere_status(status)
        print(status["ergebnis"], file=sys.stderr)
        return 1
    status["ergebnis"] = "ok"
    status["neu_gemeldet"] = neu
    if neu:
        status["letzte_meldung"] = status["letzter_lauf"]
        status["letzte_treffer"] = neu
    else:
        alt = pc.lade_status()
        for k in ("letzte_meldung", "letzte_treffer"):
            if k in alt:
                status[k] = alt[k]
    pc.speichere_status(status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
