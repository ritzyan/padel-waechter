import json
import os
import datetime as dt

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE, "config.json")
STATUS_FILE = os.path.join(BASE, "status.json")

STANDARD = {
    "aktiv": True,
    "wochentage": [0],      # 0 = Montag ... 6 = Sonntag
    "start_von": "20:00",   # früheste Startzeit
    "start_bis": "20:00",   # späteste Startzeit
    "dauer_min": 90,
    "tage_im_voraus": 14,
}


def lade_env():
    pfad = os.path.join(BASE, ".env")
    if os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as f:
            for zeile in f:
                zeile = zeile.strip()
                if zeile and not zeile.startswith("#") and "=" in zeile:
                    k, v = zeile.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def _zeit_ok(text):
    try:
        dt.datetime.strptime(text, "%H:%M")
        return True
    except (TypeError, ValueError):
        return False


def bereinige(roh):
    """Macht aus beliebigen Eingaben eine gültige Konfiguration."""
    cfg = dict(STANDARD)
    cfg["aktiv"] = bool(roh.get("aktiv", STANDARD["aktiv"]))

    tage = []
    for t in roh.get("wochentage", STANDARD["wochentage"]):
        try:
            t = int(t)
        except (TypeError, ValueError):
            continue
        if 0 <= t <= 6 and t not in tage:
            tage.append(t)
    cfg["wochentage"] = sorted(tage)

    von = roh.get("start_von", STANDARD["start_von"])
    bis = roh.get("start_bis", STANDARD["start_bis"])
    if _zeit_ok(von):
        cfg["start_von"] = von
    if _zeit_ok(bis):
        cfg["start_bis"] = bis
    if cfg["start_bis"] < cfg["start_von"]:
        cfg["start_bis"] = cfg["start_von"]

    try:
        d = int(roh.get("dauer_min", STANDARD["dauer_min"]))
        cfg["dauer_min"] = d if 30 <= d <= 240 else STANDARD["dauer_min"]
    except (TypeError, ValueError):
        pass

    try:
        n = int(roh.get("tage_im_voraus", STANDARD["tage_im_voraus"]))
        cfg["tage_im_voraus"] = n if 1 <= n <= 30 else STANDARD["tage_im_voraus"]
    except (TypeError, ValueError):
        pass
    return cfg


def lade_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return bereinige(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(STANDARD)


def speichere_config(cfg):
    cfg = bereinige(cfg)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG_FILE)
    return cfg


def lade_status():
    try:
        with open(STATUS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def speichere_status(status):
    tmp = STATUS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATUS_FILE)
