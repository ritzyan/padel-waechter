import os
import sys
import datetime as dt
from zoneinfo import ZoneInfo
import requests

import padel_config as pc

pc.lade_env()

TOPIC = os.environ["NTFY_TOPIC"]

STATE_FILE = os.path.join(pc.BASE, "gemeldet.txt")
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

HEADERS = {
    "accept": "*/*",
    "accept-language": "de,de-DE;q=0.9,en;q=0.8",
    "cookie": "pt_web_opened=1",
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


def club_url(club):
    return f"https://playtomic.com/clubs/{club['slug']}"


def freie_startzeiten(club, tag, cfg):
    """Gibt die passenden freien Startzeiten (HH:MM) eines Clubs für einen Tag zurück."""
    r = requests.get(
        "https://playtomic.com/api/clubs/availability",
        params={"tenant_id": club["tenant_id"], "date": str(tag), "sport_id": "PADEL"},
        headers={**HEADERS, "referer": club_url(club)},
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


def push(text, link):
    r = requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=text.encode("utf-8"),
        headers={"Title": "Padel-Slot frei", "Click": link},
        timeout=30,
    )
    r.raise_for_status()


def pruefe_club(club, cfg, schon):
    """Prüft einen Club, meldet neue Treffer und gibt sie zurück."""
    neu = []
    for tag in ziel_tage(cfg):
        zeiten = [z for z in freie_startzeiten(club, tag, cfg)
                  if f"{club['slug']} {tag} {z}" not in schon]
        if not zeiten:
            continue
        text = (
            f"{club['name']}: {WOCHENTAGE[tag.weekday()]} {tag.strftime('%d.%m.')} frei um "
            f"{', '.join(zeiten)} Uhr ({cfg['dauer_min']} Min). Jetzt buchen!"
        )
        push(text, club_url(club))
        with open(STATE_FILE, "a") as f:
            for z in zeiten:
                f.write(f"{club['slug']} {tag} {z}\n")
        neu.extend(f"{club['name']} {tag.strftime('%d.%m.')} {z}" for z in zeiten)
    return neu


def pruefe(cfg):
    """Prüft alle aktiven Clubs. Ein Fehler bei einem Club stoppt die anderen nicht."""
    schon = gemeldet()
    neu, fehler = [], []
    for club in cfg["clubs"]:
        if not club["aktiv"]:
            continue
        try:
            neu.extend(pruefe_club(club, cfg, schon))
        except Exception as e:
            fehler.append(f"{club['name']}: {e}")
    return neu, fehler


def main():
    cfg = pc.lade_config()
    status = {"letzter_lauf": jetzt().strftime("%d.%m.%Y %H:%M:%S")}
    if not cfg["aktiv"]:
        status["ergebnis"] = "pausiert"
        pc.speichere_status(status)
        return 0
    neu, fehler = pruefe(cfg)
    status["ergebnis"] = "Fehler: " + "; ".join(fehler) if fehler else "ok"
    if fehler:
        print(status["ergebnis"], file=sys.stderr)
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
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
