"""
Erzeugt die HTML-Seite (Tipps + Bedienknoepfe).

Die Knoepfe sind Telegram-Deeplinks. Das ist Absicht: eine statische Seite kann
kein Geheimnis speichern, ein API-Schluessel im Quelltext waere oeffentlich.
Der Umweg ueber Telegram loest das, ohne dass irgendwo ein Token sichtbar wird.
"""

import html
from datetime import datetime
from zoneinfo import ZoneInfo

from tippsystem import formatiere_zeit

TZ = ZoneInfo("Europe/Berlin")

MODI = [
    ("standard", "5 Stunden vorher", "Standard. Pro Spiel, fuenf Stunden vor Anpfiff."),
    ("freitag", "Freitag frueh", "Alle Tipps des Spieltags auf einmal, sobald verfuegbar."),
    ("spaet", "30 Minuten vorher", "Spaetester Stand, Aufstellungen sind eingepreist."),
]

CSS = """
*{box-sizing:border-box}
:root{
  --bg:#f6f7f9; --karte:#ffffff; --text:#16181d; --leise:#6b7280;
  --rand:#e3e6ea; --akzent:#1f6feb; --akzent-text:#ffffff; --gut:#0f7b4f;
  --warn:#8a5a00; --warn-bg:#fdf6e3;
}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
  --bg:#0e1116; --karte:#161b22; --text:#e6edf3; --leise:#9aa4b2;
  --rand:#262c36; --akzent:#4d8ef7; --akzent-text:#0e1116; --gut:#3fb984;
  --warn:#e3b341; --warn-bg:#231d10;
}}
:root[data-theme=dark]{
  --bg:#0e1116; --karte:#161b22; --text:#e6edf3; --leise:#9aa4b2;
  --rand:#262c36; --akzent:#4d8ef7; --akzent-text:#0e1116; --gut:#3fb984;
  --warn:#e3b341; --warn-bg:#231d10;
}
body{margin:0;padding:20px 16px 56px;background:var(--bg);color:var(--text);
  font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  -webkit-text-size-adjust:100%}
.huelle{max-width:760px;margin:0 auto}
h1{font-size:1.45rem;margin:0 0 2px;letter-spacing:-.02em}
.unterzeile{color:var(--leise);font-size:.85rem;margin-bottom:22px}
.karte{background:var(--karte);border:1px solid var(--rand);border-radius:12px;
  padding:16px;margin-bottom:14px}
.karte h2{font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;
  color:var(--leise);margin:0 0 12px;font-weight:600}
.knopf{display:block;width:100%;padding:13px 16px;margin-bottom:8px;
  background:var(--akzent);color:var(--akzent-text);text-decoration:none;
  border-radius:9px;font-weight:600;text-align:center;font-size:.95rem}
.knopf.neben{background:transparent;color:var(--text);border:1px solid var(--rand);
  font-weight:500;text-align:left;display:flex;justify-content:space-between;
  align-items:center;gap:10px}
.knopf.neben.an{border-color:var(--akzent);color:var(--akzent)}
.knopf small{display:block;font-weight:400;color:var(--leise);font-size:.78rem;
  margin-top:2px}
.haken{font-weight:700}
table{width:100%;border-collapse:collapse;font-size:.92rem}
th{text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;
  color:var(--leise);font-weight:600;padding:0 8px 8px 0;border-bottom:1px solid var(--rand)}
td{padding:11px 8px 11px 0;border-bottom:1px solid var(--rand);vertical-align:top}
tr:last-child td{border-bottom:none}
.tipp{font-variant-numeric:tabular-nums;font-weight:700;font-size:1.05rem;
  white-space:nowrap}
.partie{font-weight:500}
.zeit{color:var(--leise);font-size:.8rem;white-space:nowrap}
.ep{text-align:right;color:var(--leise);font-variant-numeric:tabular-nums;
  white-space:nowrap;font-size:.85rem}
.marke{display:inline-block;font-size:.68rem;padding:2px 6px;border-radius:5px;
  background:var(--warn-bg);color:var(--warn);margin-left:6px;vertical-align:1px}
.hinweis{background:var(--warn-bg);color:var(--warn);border:1px solid var(--rand);
  border-radius:10px;padding:13px 15px;font-size:.88rem;margin-bottom:14px}
.fuss{color:var(--leise);font-size:.76rem;line-height:1.65;margin-top:22px}
.zahlen{display:flex;gap:18px;flex-wrap:wrap;margin-top:4px}
.zahl b{display:block;font-size:1.3rem;font-variant-numeric:tabular-nums}
.zahl span{color:var(--leise);font-size:.74rem}
@media(max-width:520px){.verbergen{display:none}}
"""


def _knoepfe(bot, modus_aktiv):
    if not bot:
        return ('<div class="hinweis">Kein Telegram-Bot hinterlegt. Trage in '
                '<code>config.json</code> unter <code>telegram_bot</code> den '
                'Bot-Namen ein, damit die Knoepfe funktionieren.</div>')
    basis = f"https://t.me/{html.escape(bot)}?start="
    teile = [f'<a class="knopf" href="{basis}jetzt">Tipps jetzt an Telegram senden</a>']
    teile.append('<div style="height:14px"></div>')
    for schluessel, titel, erklaerung in MODI:
        an = " an" if schluessel == modus_aktiv else ""
        haken = '<span class="haken">&#10003;</span>' if schluessel == modus_aktiv else ""
        teile.append(
            f'<a class="knopf neben{an}" href="{basis}modus_{schluessel}">'
            f'<span>{titel}<small>{erklaerung}</small></span>{haken}</a>')
    return "".join(teile)


def _tabelle(spiele):
    if not spiele:
        return ('<p style="color:var(--leise);margin:0">Zurzeit stehen keine '
                'Bundesligaspiele im Vorschau-Feed. Die Seite aktualisiert sich '
                'automatisch, sobald der naechste Spieltag dort auftaucht.</p>')
    reihen = []
    for s in spiele:
        if not s.get("tipp"):
            reihen.append(
                f'<tr><td class="tipp">&mdash;</td>'
                f'<td class="partie">{html.escape(s["home"])} &ndash; {html.escape(s["away"])}'
                f'<div class="zeit">{html.escape(s.get("hinweis", "kein Tipp"))}</div></td>'
                f'<td class="ep"></td></tr>')
            continue
        marke = ("" if s["quelle"] == "modell+markt"
                 else f'<span class="marke">{html.escape(s["quelle"])}</span>')
        zeit = formatiere_zeit(s["anstoss"])
        reihen.append(
            f'<tr><td class="tipp">{s["tipp"]}</td>'
            f'<td class="partie">{html.escape(s["home"])} &ndash; {html.escape(s["away"])}{marke}'
            f'<div class="zeit">{zeit} Uhr</div></td>'
            f'<td class="ep">EP {s["ep"]:.2f}<div class="zeit verbergen">'
            f'exakt {s["p_exakt"]*100:.0f}%</div></td></tr>')
    return (f'<table><thead><tr><th>Tipp</th><th>Partie</th>'
            f'<th style="text-align:right">Erwartung</th></tr></thead>'
            f'<tbody>{"".join(reihen)}</tbody></table>')


def daten(spiele, cfg, stand=None):
    """
    Die Tipps als reines JSON-taugliches Dict. Wird nach docs/tipps.json
    geschrieben, damit eine anderswo gehostete Seite sie laden kann.
    """
    stand = stand or datetime.now(TZ)
    modus = cfg.get("modus", "standard")
    raus = []
    for s in spiele:
        raus.append({
            "anstoss": s["anstoss"].isoformat(),
            "anstoss_text": formatiere_zeit(s["anstoss"]),
            "home": s["home"], "away": s["away"],
            "tipp": s.get("tipp"), "ep": s.get("ep"),
            "quelle": s.get("quelle"), "hinweis": s.get("hinweis", ""),
            "p_heim": s.get("p_heim"), "p_remis": s.get("p_remis"),
            "p_aus": s.get("p_aus"), "p_exakt": s.get("p_exakt"),
        })
    return {
        "stand": stand.isoformat(),
        "stand_text": stand.strftime("%d.%m.%Y, %H:%M"),
        "modus": modus,
        "modus_text": next((t for k, t, _ in MODI if k == modus), modus),
        "telegram_bot": (cfg.get("telegram_bot") or "").lstrip("@"),
        "geplant_fuer": cfg.get("geplant_fuer"),
        "spiele": raus,
    }


def json_url(cfg):
    """Rohdaten-URL der tipps.json im GitHub-Repository."""
    repo = (cfg.get("github_repo") or "").strip().strip("/")
    if not repo or "/" not in repo:
        return ""
    zweig = cfg.get("github_zweig") or "main"
    return f"https://raw.githubusercontent.com/{repo}/{zweig}/docs/tipps.json"


def baue(spiele, cfg, stand=None):
    """Baut die komplette Seite und gibt den HTML-Text zurueck."""
    stand = stand or datetime.now(TZ)
    bot = (cfg.get("telegram_bot") or "").lstrip("@")
    modus = cfg.get("modus", "standard")
    getippt = [s for s in spiele if s.get("ep") is not None]
    summe = sum(s["ep"] for s in getippt)

    modus_text = next((t for k, t, _ in MODI if k == modus), modus)
    geplant = cfg.get("geplant_fuer")
    geplant_html = ""
    if geplant:
        geplant_html = (f'<div class="hinweis">Einmalige Sendung geplant fuer '
                        f'<b>{html.escape(str(geplant))}</b>.</div>')

    return f"""<meta charset="utf-8">
<title>Bundesliga Tipps</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<div class="huelle">
  <h1>Bundesliga Tipps</h1>
  <div class="unterzeile">Stand {stand.strftime('%d.%m.%Y, %H:%M')} Uhr &middot;
    Modus: {html.escape(modus_text)}</div>

  {geplant_html}

  <div class="karte">
    <h2>Naechste Spiele</h2>
    {_tabelle(spiele)}
    <div class="zahlen" style="margin-top:16px">
      <div class="zahl"><b>{len(getippt)}</b><span>Spiele getippt</span></div>
      <div class="zahl"><b>{summe:.1f}</b><span>erwartete Punkte</span></div>
      <div class="zahl"><b>7,86</b><span>Schnitt je 9er-Spieltag (Backtest)</span></div>
    </div>
  </div>

  <div class="karte">
    <h2>Steuerung</h2>
    {_knoepfe(bot, modus)}
  </div>

  <div class="fuss">
    Modell: Dixon-Coles mit Zeitgewichtung (xi&nbsp;=&nbsp;0,006), Tendenz-Raender
    auf die Buchmacherquoten gesetzt, Tipp per Erwartungswert-Optimierung fuer die
    Wertung 3&nbsp;/&nbsp;2&nbsp;/&nbsp;1&nbsp;/&nbsp;0.<br>
    Im Walk-Forward ueber 1129 Spiele (Saisons 21/22 bis 25/26): 7,86 Punkte je
    9er-Spieltag gegenueber 7,60 fuer den blanken Buchmacher-Favoriten und 6,13
    fuer &bdquo;immer 2:1&ldquo;.<br>
    &bdquo;nur markt&ldquo; heisst, dass mindestens ein Team noch zu wenig Historie
    hat und der Tipp allein aus den Quoten stammt &ndash; normal in den ersten
    Spieltagen nach einem Aufstieg.
  </div>
</div>
"""


LIVE_JS = """
const URL_JSON = %(url)s;
const el = (t, k, x) => { const n = document.createElement(t);
  if (k) n.className = k; if (x !== undefined) n.textContent = x; return n; };

function zeigeFehler(text) {
  const k = document.getElementById('inhalt');
  k.textContent = '';
  k.appendChild(el('div', 'hinweis', text));
}

function knoepfe(bot, modus) {
  const box = document.getElementById('steuerung');
  box.textContent = '';
  if (!bot) {
    box.appendChild(el('div', 'hinweis',
      'Kein Telegram-Bot hinterlegt. Trage ihn in config.json unter telegram_bot ein.'));
    return;
  }
  const basis = 'https://t.me/' + encodeURIComponent(bot) + '?start=';
  const a = el('a', 'knopf', 'Tipps jetzt an Telegram senden');
  a.href = basis + 'jetzt'; box.appendChild(a);
  box.appendChild(Object.assign(document.createElement('div'),
    { style: 'height:14px' }));
  for (const [k, titel, erkl] of MODI) {
    const b = el('a', 'knopf neben' + (k === modus ? ' an' : ''));
    b.href = basis + 'modus_' + k;
    const s = el('span'); s.appendChild(document.createTextNode(titel));
    s.appendChild(el('small', null, erkl)); b.appendChild(s);
    if (k === modus) b.appendChild(el('span', 'haken', '\u2713'));
    box.appendChild(b);
  }
}

function tabelle(spiele) {
  if (!spiele.length) return el('p', null,
    'Zurzeit stehen keine Bundesligaspiele im Vorschau-Feed.');
  const t = el('table'), kopf = el('thead'), zr = el('tr');
  for (const [txt, rechts] of [['Tipp', 0], ['Partie', 0], ['Erwartung', 1]]) {
    const th = el('th', null, txt);
    if (rechts) th.style.textAlign = 'right';
    zr.appendChild(th);
  }
  kopf.appendChild(zr); t.appendChild(kopf);
  const body = el('tbody');
  for (const s of spiele) {
    const r = el('tr');
    r.appendChild(el('td', 'tipp', s.tipp || '\u2014'));
    const mitte = el('td', 'partie');
    mitte.appendChild(document.createTextNode(s.home + ' \u2013 ' + s.away));
    if (s.tipp && s.quelle !== 'modell+markt')
      mitte.appendChild(el('span', 'marke', s.quelle));
    mitte.appendChild(el('div', 'zeit',
      s.tipp ? s.anstoss_text + ' Uhr' : (s.hinweis || 'kein Tipp')));
    r.appendChild(mitte);
    const rechts = el('td', 'ep', s.ep != null ? 'EP ' + s.ep.toFixed(2) : '');
    if (s.p_exakt != null) rechts.appendChild(
      el('div', 'zeit verbergen', 'exakt ' + Math.round(s.p_exakt * 100) + '%%'));
    r.appendChild(rechts);
    body.appendChild(r);
  }
  t.appendChild(body);
  return t;
}

async function laden() {
  if (!URL_JSON) {
    zeigeFehler('Keine Datenquelle eingetragen. Setze github_repo in config.json '
      + 'auf "benutzername/repository" und lass run.py einmal laufen.');
    return;
  }
  let d;
  try {
    const antwort = await fetch(URL_JSON + '?t=' + Date.now(), { cache: 'no-store' });
    if (!antwort.ok) throw new Error('HTTP ' + antwort.status);
    d = await antwort.json();
  } catch (e) {
    zeigeFehler('Tipps konnten nicht geladen werden (' + e.message + '). '
      + 'Steht das Repository auf oeffentlich und ist run.py schon gelaufen?');
    return;
  }
  document.getElementById('unterzeile').textContent =
    'Stand ' + d.stand_text + ' Uhr \u00b7 Modus: ' + d.modus_text;
  const inhalt = document.getElementById('inhalt');
  inhalt.textContent = '';
  if (d.geplant_fuer) inhalt.appendChild(el('div', 'hinweis',
    'Einmalige Sendung geplant fuer ' + d.geplant_fuer.slice(0, 16).replace('T', ' ') + '.'));
  const karte = el('div', 'karte');
  karte.appendChild(el('h2', null, 'Naechste Spiele'));
  karte.appendChild(tabelle(d.spiele));
  const getippt = d.spiele.filter(s => s.ep != null);
  const zahlen = el('div', 'zahlen'); zahlen.style.marginTop = '16px';
  for (const [wert, txt] of [[String(getippt.length), 'Spiele getippt'],
      [getippt.reduce((a, s) => a + s.ep, 0).toFixed(1), 'erwartete Punkte'],
      ['7,86', 'Schnitt je 9er-Spieltag (Backtest)']]) {
    const z = el('div', 'zahl'); z.appendChild(el('b', null, wert));
    z.appendChild(el('span', null, txt)); zahlen.appendChild(z);
  }
  karte.appendChild(zahlen); inhalt.appendChild(karte);
  knoepfe(d.telegram_bot, d.modus);
}

laden();
setInterval(laden, 120000);   // alle zwei Minuten nachsehen
document.addEventListener('visibilitychange',
  () => { if (!document.hidden) laden(); });
"""


def baue_live(cfg):
    """
    Eigenstaendige Seite, die die Tipps beim Oeffnen aus dem GitHub-Repository
    laedt. Einmal irgendwo veroeffentlichen, danach bleibt sie aktuell.
    """
    import json as _json
    modi_js = "[" + ",".join(
        "[%s,%s,%s]" % (_json.dumps(k), _json.dumps(t), _json.dumps(e))
        for k, t, e in MODI) + "]"
    js = LIVE_JS % {"url": _json.dumps(json_url(cfg))}
    return f"""<meta charset="utf-8">
<title>Bundesliga Tipps</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<div class="huelle">
  <h1>Bundesliga Tipps</h1>
  <div class="unterzeile" id="unterzeile">wird geladen \u2026</div>
  <div id="inhalt"></div>
  <div class="karte"><h2>Steuerung</h2><div id="steuerung"></div></div>
  <div class="fuss">
    Dixon-Coles mit Zeitgewichtung, Tendenz-Raender auf die Buchmacherquoten
    gesetzt, Tipp per Erwartungswert-Optimierung fuer die Wertung 3/2/1/0.
    Im Walk-Forward ueber 1129 Spiele: 7,86 Punkte je 9er-Spieltag gegenueber
    7,60 fuer den blanken Buchmacher-Favoriten und 6,13 fuer &bdquo;immer 2:1&ldquo;.
  </div>
</div>
<script>
const MODI = {modi_js};
{js}
</script>
"""
