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
<meta name="theme-color" content="#1e56c8">
<title>Padel-Wächter</title>
<style>
  :root {
    --court: #1e56c8; --court-dark: #123a94; --line: #f5f8ff;
    --ball: #d6f23c; --ink: #0b1b44; --sheet: #f4f7ff; --mute: #5a6a94;
    --ok: #12805a; --bad: #d6343a;
  }
  * { box-sizing: border-box; }
  html { background: var(--sheet); }
  body { margin: 0; background: var(--court); color: var(--line);
         font-family: ui-rounded, "SF Pro Rounded", "Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif;
         line-height: 1.4; -webkit-font-smoothing: antialiased; }
  main { max-width: 520px; margin: 0 auto; padding: 22px 16px 0; }
  h1 { margin: 0; font-size: 2rem; font-weight: 850; letter-spacing: -0.03em; line-height: 1.05; }
  .unter { margin: 6px 0 0; opacity: .8; }

  /* Der Platz ist der Schalter */
  .court-form { margin: 20px 0 0; }
  .court { display: block; width: 100%; padding: 0; border: 0; background: none; cursor: pointer;
           border-radius: 18px; -webkit-tap-highlight-color: transparent; }
  .court svg { display: block; width: 100%; height: auto; }
  .court .flaeche { fill: var(--court-dark); }
  .court .linien { stroke: var(--line); stroke-width: 3; fill: none; stroke-linecap: round;
                   transition: opacity .35s; }
  .court .netz { stroke: var(--line); stroke-width: 5; stroke-dasharray: 2 7; stroke-linecap: round; }
  .court .ball { transition: transform .38s cubic-bezier(.3,.7,.2,1); }
  .court .glow { fill: var(--ball); opacity: 0; transition: opacity .38s; }
  .court.aus .linien { opacity: .35; }
  .court.aus .ball { transform: translateX(-120px); }
  .court.aus .ballkoerper { fill: #9fb0d8; }
  .court.an .ball { transform: translateX(120px); }
  .court.an .glow { opacity: .2; }
  .court.an .ballkoerper { fill: var(--ball); }
  .court:focus-visible, button:focus-visible, input:focus-visible + span, input:focus-visible,
  a:focus-visible { outline: 3px solid var(--ball); outline-offset: 3px; }
  .zustand { margin: 12px 2px 0; display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
  .zustand strong { font-size: 1.5rem; font-weight: 850; letter-spacing: -0.02em; }
  .zustand span { opacity: .8; font-size: .95rem; text-align: right; }

  .meldung { margin: 14px 0 0; padding: 11px 14px; border-radius: 12px; background: var(--ball); color: var(--ink);
             font-weight: 700; }

  .status { margin: 18px 0 26px; display: grid; gap: 10px; }
  .status p { margin: 0; font-size: .95rem; opacity: .9; }
  .pille { display: inline-block; padding: 3px 11px; border-radius: 99px; background: var(--line); color: var(--ok);
           font-weight: 800; font-size: .88rem; }
  .pille.fehler { color: var(--bad); }
  .pille.pause { color: var(--mute); }
  .status form { margin: 0; }
  .jetzt { width: 100%; padding: 14px; border: 0; border-radius: 14px; background: var(--ball); color: var(--ink);
           font: inherit; font-weight: 800; font-size: 1.05rem; cursor: pointer; }
  .jetzt:active { transform: translateY(1px); }

  /* Einstellungen als Blatt, das von unten in den Platz ragt */
  .sheet { margin: 0; padding: 8px 20px 48px; background: var(--sheet); color: var(--ink);
           border-radius: 30px 30px 0 0; }
  .sheet-inner { max-width: 520px; margin: 0 auto; }
  fieldset { border: 0; margin: 0; padding: 22px 0; border-bottom: 1px solid #1b2f6b1f; min-width: 0; }
  fieldset:last-of-type { border-bottom: 0; }
  legend { padding: 0; font-size: 1.1rem; font-weight: 800; letter-spacing: -0.01em; margin-bottom: 12px; }
  .hinweis { margin: -4px 0 12px; font-size: .9rem; color: var(--mute); }

  .opt input { position: absolute; opacity: 0; pointer-events: none; }
  .opt { position: relative; display: block; cursor: pointer; }
  .opt > span { display: flex; align-items: center; justify-content: center; user-select: none;
                transition: background .15s, color .15s, border-color .15s; }

  .tage { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
  .tage .opt > span { aspect-ratio: 1; border-radius: 50%; border: 2px solid #1b2f6b33; font-weight: 800; }
  .tage input:checked + span { background: var(--court); border-color: var(--court); color: #fff; }

  .clubs { display: grid; gap: 8px; }
  .clubs .opt > span { justify-content: flex-start; gap: 12px; padding: 14px 16px; border-radius: 16px;
                       border: 2px solid #1b2f6b33; font-weight: 750; }
  .clubs .opt > span::before { content: ""; width: 18px; height: 18px; border-radius: 50%;
                               border: 2px solid #1b2f6b55; flex: none; }
  .clubs input:checked + span { border-color: var(--court); background: #e6edff; }
  .clubs input:checked + span::before { background: var(--ball); border-color: var(--ink);
                                        box-shadow: inset 0 0 0 3px #e6edff; }

  .zeiten { display: flex; align-items: center; gap: 12px; }
  .zeiten span { color: var(--mute); }
  input[type=time] { flex: 1; min-width: 0; font: inherit; font-size: 1.25rem; font-weight: 800;
                     font-variant-numeric: tabular-nums; color: var(--ink); background: #fff;
                     border: 2px solid #1b2f6b33; border-radius: 14px; padding: 10px 8px; }

  .dauer { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .dauer .opt > span { padding: 13px 4px; border-radius: 14px; border: 2px solid #1b2f6b33; font-weight: 800; }
  .dauer input:checked + span { background: var(--court); border-color: var(--court); color: #fff; }

  .tageZahl { display: flex; align-items: center; gap: 16px; }
  .tageZahl output { min-width: 3.4ch; font-size: 1.8rem; font-weight: 850; font-variant-numeric: tabular-nums; }
  input[type=range] { flex: 1; accent-color: var(--court); height: 32px; }

  .speichern { width: 100%; margin-top: 8px; padding: 16px; border: 0; border-radius: 16px; background: var(--ink);
               color: #fff; font: inherit; font-weight: 800; font-size: 1.05rem; cursor: pointer; }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<main>
  <h1>Padel-Wächter</h1>
  <p class="unter">Meldet freie Plätze per Push aufs Handy.</p>

  <form class="court-form" method="post" action="{{ url_for('umschalten') }}" id="umschalter">
    <button type="submit" class="court {{ 'an' if cfg.aktiv else 'aus' }}" id="court"
            role="switch" aria-checked="{{ 'true' if cfg.aktiv else 'false' }}"
            aria-label="{{ 'Ausschalten' if cfg.aktiv else 'Einschalten' }}">
      <svg viewBox="0 0 400 210" aria-hidden="true">
        <rect class="flaeche" x="0" y="0" width="400" height="210" rx="18"/>
        <g class="linien">
          <rect x="22" y="20" width="356" height="170" rx="4"/>
          <line x1="130" y1="20" x2="130" y2="190"/>
          <line x1="270" y1="20" x2="270" y2="190"/>
          <line x1="130" y1="105" x2="270" y2="105"/>
        </g>
        <line class="netz" x1="200" y1="14" x2="200" y2="196"/>
        <g class="ball">
          <circle class="glow" cx="200" cy="105" r="36"/>
          <circle class="ballkoerper" cx="200" cy="105" r="16" fill="#d6f23c"/>
          <path d="M187 99 q13 -10 26 0 M187 111 q13 10 26 0" fill="none" stroke="#0b1b44" stroke-width="1.6"
                stroke-linecap="round" opacity=".55"/>
        </g>
      </svg>
    </button>
  </form>
  <div class="zustand">
    <strong>{{ 'Aktiv' if cfg.aktiv else 'Pausiert' }}</strong>
    <span>{{ 'Prüft alle 15 Minuten.' if cfg.aktiv else 'Es wird nichts geprüft.' }}</span>
  </div>

  {% if meldung %}<div class="meldung" role="status">{{ meldung }}</div>{% endif %}

  <section class="status">
    {% set erg = status.get('ergebnis', '') %}
    <p>Letzter Lauf: {{ status.get('letzter_lauf', 'noch keiner') }}
      {% if erg %}<span class="pille {{ 'fehler' if erg.startswith('Fehler') else ('pause' if erg == 'pausiert' else '') }}">
        {{ erg if erg.startswith('Fehler') or erg == 'pausiert' else 'ok' }}</span>{% endif %}</p>
    <p>Letzte Meldung: {{ status.get('letzte_meldung', 'noch keine') }}
      {% if status.get('letzte_treffer') %}({{ status.letzte_treffer | join(', ') }}){% endif %}</p>
    <form method="post" action="{{ url_for('jetzt_pruefen') }}">
      <button class="jetzt">Jetzt prüfen</button>
    </form>
  </section>
</main>

<div class="sheet"><div class="sheet-inner">
<form method="post" action="{{ url_for('speichern') }}">
  <fieldset>
    <legend>Clubs</legend>
    <div class="clubs">
      {% for club in cfg.clubs %}
      <label class="opt"><input type="checkbox" name="clubs" value="{{ club.slug }}" {{ 'checked' if club.aktiv }}>
        <span>{{ club.name }}</span></label>
      {% endfor %}
    </div>
  </fieldset>

  <fieldset>
    <legend>Wochentage</legend>
    <div class="tage">
      {% for name in tage %}
      <label class="opt"><input type="checkbox" name="wochentage" value="{{ loop.index0 }}"
        {{ 'checked' if loop.index0 in cfg.wochentage }}><span>{{ name }}</span></label>
      {% endfor %}
    </div>
  </fieldset>

  <fieldset>
    <legend>Startzeit</legend>
    <p class="hinweis">Gemeldet wird, wenn ein Platz in diesem Zeitfenster startet.</p>
    <div class="zeiten">
      <input type="time" name="start_von" value="{{ cfg.start_von }}" required aria-label="Frühester Start">
      <span>bis</span>
      <input type="time" name="start_bis" value="{{ cfg.start_bis }}" required aria-label="Spätester Start">
    </div>
  </fieldset>

  <fieldset>
    <legend>Dauer</legend>
    <div class="dauer">
      {% for d in [60, 90, 120] %}
      <label class="opt"><input type="radio" name="dauer_min" value="{{ d }}" {{ 'checked' if cfg.dauer_min == d }}>
        <span>{{ d }} Min</span></label>
      {% endfor %}
    </div>
  </fieldset>

  <fieldset>
    <legend>Wie weit im Voraus</legend>
    <div class="tageZahl">
      <input type="range" name="tage_im_voraus" min="1" max="30" value="{{ cfg.tage_im_voraus }}"
             oninput="this.nextElementSibling.textContent = this.value + ' Tage'" aria-label="Tage im Voraus">
      <output>{{ cfg.tage_im_voraus }} Tage</output>
    </div>
  </fieldset>

  <button class="speichern">Speichern</button>
</form>
</div></div>

<script>
  // Der Ball rollt zur anderen Seite, dann wird gespeichert.
  var f = document.getElementById("umschalter"), c = document.getElementById("court");
  f.addEventListener("submit", function (e) {
    if (f.dataset.gesendet) return;
    e.preventDefault();
    f.dataset.gesendet = "1";
    c.classList.toggle("an"); c.classList.toggle("aus");
    setTimeout(function () { f.submit(); }, 380);
  });
</script>
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
