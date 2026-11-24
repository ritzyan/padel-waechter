import os
import subprocess
import sys
from flask import Flask, Response, redirect, render_template_string, request, url_for

import padel_config as pc

pc.lade_env()

app = Flask(__name__)
PASSWORT = os.environ.get("APP_PASSWORD", "")
TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


@app.before_request
def anmeldung():
    if not PASSWORT:
        return None
    auth = request.authorization
    if auth and auth.password == PASSWORT:
        return None
    return Response("Anmeldung nötig", 401, {"WWW-Authenticate": 'Basic realm="Padel-Wächter"'})


SEITE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Padel-Wächter</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; padding: 16px; line-height: 1.4; }
  h1 { font-size: 1.4rem; margin: 8px 0 16px; }
  .karte { border: 1px solid #8884; border-radius: 12px; padding: 14px; margin-bottom: 14px; }
  .status { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .punkt { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
  .an { background: #2e9d4f; } .aus { background: #999; } .fehler { background: #d33; }
  button { font: inherit; padding: 10px 16px; border-radius: 8px; border: 1px solid #8886; cursor: pointer; }
  button.haupt { background: #2563eb; color: #fff; border-color: #2563eb; }
  button.gefahr { background: #d33; color: #fff; border-color: #d33; }
  label { display: block; margin: 12px 0 4px; font-weight: 600; }
  .tage { display: flex; flex-wrap: wrap; gap: 6px; }
  .tage label { display: inline-flex; align-items: center; gap: 4px; margin: 0; font-weight: 400;
                border: 1px solid #8886; border-radius: 8px; padding: 6px 10px; }
  input[type=time], input[type=number], select { font: inherit; padding: 8px; border-radius: 8px; border: 1px solid #8886; }
  .zeile { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .klein { font-size: .9rem; opacity: .75; }
  .meldung { background: #2563eb22; border-radius: 8px; padding: 10px; margin-bottom: 14px; }
</style>
</head>
<body>
<h1>Padel-Wächter · Club Weinstraße</h1>

{% if meldung %}<div class="meldung">{{ meldung }}</div>{% endif %}

<div class="karte status">
  <div>
    <span class="punkt {{ 'an' if cfg.aktiv else 'aus' }}"></span>
    <strong>{{ 'Aktiv' if cfg.aktiv else 'Pausiert' }}</strong>
  </div>
  <form method="post" action="{{ url_for('umschalten') }}">
    <button class="{{ 'gefahr' if cfg.aktiv else 'haupt' }}">{{ 'Ausschalten' if cfg.aktiv else 'Einschalten' }}</button>
  </form>
</div>

<form class="karte" method="post" action="{{ url_for('speichern') }}">
  <strong>Abfragezeitraum</strong>

  <label>Clubs</label>
  <div class="tage">
    {% for club in cfg.clubs %}
      <label><input type="checkbox" name="clubs" value="{{ club.slug }}"
        {{ 'checked' if club.aktiv }}> {{ club.name }}</label>
    {% endfor %}
  </div>

  <label>Wochentage</label>
  <div class="tage">
    {% for name in tage %}
      <label><input type="checkbox" name="wochentage" value="{{ loop.index0 }}"
        {{ 'checked' if loop.index0 in cfg.wochentage }}> {{ name }}</label>
    {% endfor %}
  </div>

  <label>Startzeit zwischen</label>
  <div class="zeile">
    <input type="time" name="start_von" value="{{ cfg.start_von }}" required>
    <span>und</span>
    <input type="time" name="start_bis" value="{{ cfg.start_bis }}" required>
  </div>

  <label>Dauer</label>
  <select name="dauer_min">
    {% for d in [60, 90, 120] %}
      <option value="{{ d }}" {{ 'selected' if cfg.dauer_min == d }}>{{ d }} Minuten</option>
    {% endfor %}
  </select>

  <label>Wie viele Tage im Voraus prüfen</label>
  <input type="number" name="tage_im_voraus" min="1" max="30" value="{{ cfg.tage_im_voraus }}">

  <p><button class="haupt">Speichern</button></p>
</form>

<div class="karte">
  <strong>Status</strong>
  <p class="klein" style="margin:8px 0">
    Letzter Lauf: {{ status.get('letzter_lauf', 'noch keiner') }}<br>
    Ergebnis:
    <span class="punkt {{ 'fehler' if status.get('ergebnis', '').startswith('Fehler') else 'an' }}"></span>{{ status.get('ergebnis', '–') }}<br>
    Letzte Meldung: {{ status.get('letzte_meldung', 'noch keine') }}
    {% if status.get('letzte_treffer') %}({{ status.letzte_treffer | join(', ') }}){% endif %}
  </p>
  <form method="post" action="{{ url_for('jetzt_pruefen') }}">
    <button>Jetzt prüfen</button>
  </form>
  <p class="klein">Der Wächter läuft automatisch alle 15 Minuten.</p>
</div>
</body>
</html>
"""


def render(meldung=None):
    return render_template_string(
        SEITE, cfg=pc.lade_config(), status=pc.lade_status(), tage=TAGE, meldung=meldung
    )


@app.get("/")
def start():
    return render(request.args.get("m"))


@app.post("/umschalten")
def umschalten():
    cfg = pc.lade_config()
    cfg["aktiv"] = not cfg["aktiv"]
    pc.speichere_config(cfg)
    return redirect(url_for("start", m="Eingeschaltet." if cfg["aktiv"] else "Ausgeschaltet."))


@app.post("/speichern")
def speichern():
    cfg = pc.lade_config()
    gewaehlt = set(request.form.getlist("clubs"))
    for club in cfg["clubs"]:
        club["aktiv"] = club["slug"] in gewaehlt
    cfg["wochentage"] = request.form.getlist("wochentage")
    cfg["start_von"] = request.form.get("start_von", "")
    cfg["start_bis"] = request.form.get("start_bis", "")
    cfg["dauer_min"] = request.form.get("dauer_min", "")
    cfg["tage_im_voraus"] = request.form.get("tage_im_voraus", "")
    gespeichert = pc.speichere_config(cfg)
    if not any(c["aktiv"] for c in gespeichert["clubs"]):
        return redirect(url_for("start", m="Gespeichert, aber ohne Club wird nichts geprüft."))
    if not gespeichert["wochentage"]:
        return redirect(url_for("start", m="Gespeichert, aber ohne Wochentag wird nichts geprüft."))
    return redirect(url_for("start", m="Gespeichert."))


@app.post("/jetzt")
def jetzt_pruefen():
    try:
        subprocess.run([sys.executable, os.path.join(pc.BASE, "check_slot.py")],
                       cwd=pc.BASE, timeout=90, capture_output=True)
    except subprocess.TimeoutExpired:
        return redirect(url_for("start", m="Prüfung dauerte zu lange."))
    return redirect(url_for("start", m="Prüfung abgeschlossen."))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
