"""
Ein Durchlauf des Tippsystems. Gedacht fuer einen Cronjob alle paar Minuten.

Ablauf:
  1. Telegram-Befehle abholen und Konfiguration anpassen
  2. Historie und Spielplan laden, Tipps rechnen
  3. pruefen, welche Spiele nach der eingestellten Vorlaufzeit faellig sind
  4. faellige Tipps per Telegram schicken, Seite immer neu schreiben

Aufruf:
  python run.py               ein normaler Durchlauf
  python run.py --probe       rechnet und zeigt alles, sendet nichts, aendert nichts
  python run.py --jetzt       schickt sofort alle anstehenden Tipps
  python run.py --nur-seite   schreibt nur die HTML-Seite neu
"""

import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import notify
import page
from tippsystem import formatiere_zeit, hole_historie, hole_spielplan, spiel_id, tippe

HIER = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HIER, "config.json")
STATE = os.path.join(HIER, "state.json")
DOCS = os.path.join(HIER, "docs")
SEITE = os.path.join(DOCS, "index.html")
DATEN_JSON = os.path.join(DOCS, "tipps.json")
SEITE_LIVE = os.path.join(DOCS, "sites.html")
TZ = ZoneInfo("Europe/Berlin")

STANDARD_CONFIG = {
    "modus": "standard",
    "vorlauf_stunden": 5.0,
    "vorlauf_freitag_stunden": 72.0,
    "vorlauf_spaet_stunden": 0.5,
    "sofort_senden": False,
    "geplant_fuer": None,
    "telegram_bot": "",
    "telegram_chat_id": "",
    # fuer die anderswo gehostete Seite (z.B. ChatGPT Sites):
    # "benutzername/repository", damit sie die Tipps laden kann
    "github_repo": "",
    "github_zweig": "main",
}


# ---------------------------------------------------------------- Ablage

def lade(pfad, standard):
    if not os.path.exists(pfad):
        return dict(standard)
    try:
        with open(pfad, encoding="utf-8") as f:
            return {**standard, **json.load(f)}
    except Exception as e:
        print(f"  {os.path.basename(pfad)} unlesbar ({e}) - nutze Standardwerte")
        return dict(standard)


def schreibe(pfad, daten):
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------- Befehle

def _zeitpunkt(text):
    """'09:00' oder '2026-08-22 09:00' oder '2026-08-22T09:00' -> ISO-String."""
    text = text.strip().replace("T", " ")
    jetzt = datetime.now(TZ)
    for muster, nur_zeit in [("%Y-%m-%d %H:%M", False), ("%d.%m.%Y %H:%M", False),
                             ("%d.%m. %H:%M", False), ("%H:%M", True)]:
        try:
            t = datetime.strptime(text, muster)
        except ValueError:
            continue
        if nur_zeit:
            t = jetzt.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            if t <= jetzt:
                t += timedelta(days=1)
        else:
            if t.year == 1900:
                t = t.replace(year=jetzt.year)
            t = t.replace(tzinfo=TZ)
        return t.isoformat()
    return None


def verarbeite_befehle(cfg, state):
    """Holt Telegram-Nachrichten und passt die Konfiguration an."""
    if not notify.aktiv():
        return cfg, state, []
    befehle, neuer_offset = notify.hole_befehle(state.get("telegram_offset", 0))
    state["telegram_offset"] = neuer_offset
    antworten = []

    for text, chat_id in befehle:
        # Erste Nachricht an den Bot legt die Chat-ID fest
        if not cfg.get("telegram_chat_id"):
            cfg["telegram_chat_id"] = chat_id
            antworten.append((chat_id, "Chat verbunden. Ab jetzt kommen die Tipps hier an."))
        if str(chat_id) != str(cfg.get("telegram_chat_id")):
            continue  # fremde Chats ignorieren

        t = text.strip()
        # Deeplinks von der Seite kommen als "/start jetzt" bzw. "/start modus_spaet"
        if t.startswith("/start"):
            rest = t[len("/start"):].strip()
            t = "/" + rest.replace("modus_", "modus ") if rest else "/status"

        wort = t.split()[0].lower().lstrip("/")
        arg = t[len(wort) + 1:].strip().lstrip("/").strip()

        if wort == "jetzt":
            cfg["sofort_senden"] = True
            antworten.append((chat_id, "Alles klar, die Tipps kommen gleich."))
        elif wort == "modus":
            gueltig = {k for k, _, _ in page.MODI}
            if arg in gueltig:
                cfg["modus"] = arg
                lead = _vorlauf(cfg, arg)
                antworten.append((chat_id, f"Modus auf <b>{arg}</b> gestellt "
                                           f"({lead:g} Stunden vor Anpfiff)."))
            else:
                antworten.append((chat_id, "Moegliche Modi: " + ", ".join(sorted(gueltig))))
        elif wort == "vorlauf":
            try:
                cfg["vorlauf_stunden"] = float(arg.replace(",", "."))
                cfg["modus"] = "standard"
                antworten.append((chat_id, f"Vorlauf auf {cfg['vorlauf_stunden']:g} "
                                           f"Stunden gesetzt."))
            except ValueError:
                antworten.append((chat_id, "Beispiel: /vorlauf 3"))
        elif wort == "um":
            iso = _zeitpunkt(arg)
            if iso:
                cfg["geplant_fuer"] = iso
                antworten.append((chat_id, f"Einmalige Sendung geplant fuer "
                                           f"{iso[:16].replace('T', ' ')} Uhr."))
            else:
                antworten.append((chat_id, "Beispiel: /um 09:00 oder /um 22.08.2026 09:00"))
        elif wort == "status":
            antworten.append((chat_id, _status(cfg)))
        elif wort in ("hilfe", "help"):
            antworten.append((chat_id, HILFE))
    return cfg, state, antworten


HILFE = ("<b>Befehle</b>\n"
         "/jetzt &mdash; alle anstehenden Tipps sofort schicken\n"
         "/modus standard | freitag | spaet\n"
         "/vorlauf 3 &mdash; Stunden vor Anpfiff (Modus standard)\n"
         "/um 09:00 &mdash; einmalige Sendung zu diesem Zeitpunkt\n"
         "/status &mdash; aktuelle Einstellung")


def _status(cfg):
    zeilen = [f"<b>Modus:</b> {cfg['modus']} ({_vorlauf(cfg, cfg['modus']):g} h vor Anpfiff)"]
    if cfg.get("geplant_fuer"):
        zeilen.append(f"<b>Geplant:</b> {cfg['geplant_fuer'][:16].replace('T', ' ')} Uhr")
    return "\n".join(zeilen)


# ---------------------------------------------------------------- Faelligkeit

def _vorlauf(cfg, modus):
    return float({
        "standard": cfg.get("vorlauf_stunden", 5.0),
        "freitag": cfg.get("vorlauf_freitag_stunden", 72.0),
        "spaet": cfg.get("vorlauf_spaet_stunden", 0.5),
    }.get(modus, cfg.get("vorlauf_stunden", 5.0)))


def faellige(spiele, cfg, state, jetzt):
    """
    Waehlt die Spiele aus, deren Tipp jetzt verschickt werden soll.
    Ein Spiel wird erneut geschickt, wenn sich der Modus seit dem letzten Mal
    geaendert hat - dann ist der Tipp auf einem neueren Datenstand.
    """
    modus = cfg.get("modus", "standard")
    gesendet = state.get("gesendet", {})
    schwelle = timedelta(hours=_vorlauf(cfg, modus))

    einmalig = bool(cfg.get("sofort_senden"))
    if cfg.get("geplant_fuer"):
        try:
            if jetzt >= datetime.fromisoformat(cfg["geplant_fuer"]):
                einmalig = True
        except ValueError:
            cfg["geplant_fuer"] = None

    raus = []
    for s in spiele:
        if s["anstoss"] <= jetzt:
            continue  # schon angepfiffen
        sid = spiel_id(s)
        if gesendet.get(sid) == modus and not einmalig:
            continue
        if einmalig or (s["anstoss"] - jetzt) <= schwelle:
            raus.append(s)
    return raus, einmalig


# ---------------------------------------------------------------- Hauptlauf

def main():
    argumente = set(sys.argv[1:])
    probe = "--probe" in argumente
    nur_seite = "--nur-seite" in argumente

    cfg = lade(CONFIG, STANDARD_CONFIG)
    state = lade(STATE, {"gesendet": {}, "telegram_offset": 0})
    jetzt = datetime.now(TZ)
    antworten = []

    if not probe and not nur_seite:
        cfg, state, antworten = verarbeite_befehle(cfg, state)
    if "--jetzt" in argumente:
        cfg["sofort_senden"] = True

    print(f"Lauf {jetzt:%d.%m.%Y %H:%M} - Modus {cfg['modus']} "
          f"({_vorlauf(cfg, cfg['modus']):g} h Vorlauf)")

    print("  Historie laden ...")
    historie = hole_historie()
    print(f"  {len(historie)} Spiele, bis {historie['date'].max():%d.%m.%Y}")

    print("  Spielplan laden ...")
    spielplan = hole_spielplan()
    if spielplan.empty:
        print("  Keine Bundesligaspiele im Vorschau-Feed.")
        spiele = []
    else:
        kommend = spielplan[[a > jetzt for a in spielplan["anstoss"]]]
        print(f"  {len(kommend)} kommende Spiele, naechster Anstoss "
              f"{kommend['anstoss'].iloc[0]:%d.%m. %H:%M}" if len(kommend) else
              "  Keine kommenden Spiele.")
        spiele = tippe(historie, kommend) if len(kommend) else []

    for s in spiele:
        print(f"    {formatiere_zeit(s['anstoss'])}  {s['home']:<16} - "
              f"{s['away']:<16}  {s.get('tipp') or '--':>4}  "
              f"EP {s.get('ep') or 0:.2f}  [{s['quelle']}]")

    dran, einmalig = faellige(spiele, cfg, state, jetzt) if spiele else ([], False)

    if probe:
        print(f"\n  Probelauf: {len(dran)} Spiele waeren jetzt faellig. "
              f"Nichts gesendet, nichts gespeichert.")
    elif nur_seite:
        print("\n  Nur Seite neu geschrieben.")
    else:
        chat = cfg.get("telegram_chat_id")
        for ziel, text in antworten:
            notify.sende(text, ziel)
        if dran:
            titel = ("Bundesliga - alle anstehenden Tipps" if einmalig
                     else f"Bundesliga - Tipps ({_vorlauf(cfg, cfg['modus']):g} h vor Anpfiff)")
            if notify.sende(notify.formatiere(dran, titel), chat):
                for s in dran:
                    state.setdefault("gesendet", {})[spiel_id(s)] = cfg["modus"]
                print(f"\n  {len(dran)} Tipps an Telegram geschickt.")
            else:
                print("\n  Senden fehlgeschlagen - Tipps bleiben faellig.")
        else:
            print("\n  Nichts faellig.")

        if einmalig:
            cfg["sofort_senden"] = False
            cfg["geplant_fuer"] = None
        # abgelaufene Eintraege aufraeumen
        grenze = (jetzt - timedelta(days=14)).date().isoformat()
        state["gesendet"] = {k: v for k, v in state.get("gesendet", {}).items()
                             if k[:10] >= grenze}
        schreibe(CONFIG, cfg)
        schreibe(STATE, state)

    os.makedirs(DOCS, exist_ok=True)
    with open(SEITE, "w", encoding="utf-8") as f:
        f.write(page.baue(spiele, cfg, jetzt))
    schreibe(DATEN_JSON, page.daten(spiele, cfg, jetzt))
    with open(SEITE_LIVE, "w", encoding="utf-8") as f:
        f.write(page.baue_live(cfg))
    print(f"  Seite geschrieben: {SEITE}")
    print(f"  Daten geschrieben: {DATEN_JSON}")
    if page.json_url(cfg):
        print(f"  Sites-Seite:       {SEITE_LIVE} (laedt von {page.json_url(cfg)})")
    else:
        print(f"  Sites-Seite:       {SEITE_LIVE} "
              f"(github_repo in config.json noch leer)")


if __name__ == "__main__":
    main()
