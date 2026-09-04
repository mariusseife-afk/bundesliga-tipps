"""
Ein Durchlauf des Tippsystems. Gedacht fuer einen Cronjob alle paar Minuten.

Ablauf:
  1. Telegram-Befehle abholen und Konfiguration anpassen
  2. Historie und Spielplan laden, Tipps rechnen
  3. pruefen, welche Nachrichten jetzt faellig sind (siehe unten)
  4. faellige Nachrichten per Telegram schicken, Seite immer neu schreiben

Feste Sende-Policy (zwei automatische Stufen, keine Modi mehr):
  - "fruehzeitig": einmal pro Spieltag, sobald die eingestellte Vorlaufzeit vor
    dem ERSTEN Spiel des Spieltags erreicht ist. Alle Spiele des Spieltags in
    EINER Nachricht (nicht 9 einzelne).
  - "kurz vorher": pro Spiel, sobald die eingestellte Vorlaufzeit vor DESSEN
    Anpfiff erreicht ist (Quoten koennen sich seit der fruehen Nachricht
    veraendert haben -> ggf. leicht anderer Tipp). Mehrere zeitgleiche Spiele
    landen in EINER Nachricht, nicht einzeln.
  Beide Schwellen bleiben nach dem Faellig-Werden dauerhaft erfuellt (bis zum
  Anpfiff) - faellt ein GitHub-Actions-Lauf aus, holt der naechste es einfach
  nach. Ist ein Spiel schon angepfiffen, wird dafuer nichts mehr verschickt
  (weder Tipp noch Hinweis) - danach ist es fuer diesen Zweck uninteressant.

Aufruf:
  python run.py               ein normaler Durchlauf
  python run.py --probe       rechnet und zeigt alles, sendet nichts, aendert nichts
  python run.py --jetzt       schickt sofort eine Nachricht mit allen anstehenden Tipps
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

# Ein Spieltag beginnt typischerweise Freitag/Samstag und endet Sonntag/Montag.
# Alles, was innerhalb dieses Fensters ab dem ersten kommenden Anstoss liegt,
# gilt als "derselbe Spieltag" fuer die gebuendelte Fruehnachricht.
RUNDEN_FENSTER = timedelta(days=4)

STANDARD_CONFIG = {
    # Vorlauf vor dem ERSTEN Spiel des Spieltags fuer die gebuendelte
    # Uebersichtsnachricht (z.B. 8h -> bei einem Freitag-20:30-Opener kommt sie
    # Freitag 12:30 Uhr).
    "vorlauf_frueh_stunden": 8.0,
    # Vorlauf vor JEDEM einzelnen Spiel fuer den zweiten, evtl. aktualisierten Tipp.
    "vorlauf_spaet_stunden": 1.5,
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
        # Deeplinks von der Seite kommen als "/start jetzt"
        if t.startswith("/start"):
            rest = t[len("/start"):].strip()
            t = "/" + rest if rest else "/status"

        wort = t.split()[0].lower().lstrip("/")
        arg = t[len(wort) + 1:].strip().lstrip("/").strip()

        if wort == "jetzt":
            cfg["sofort_senden"] = True
            antworten.append((chat_id, "Alles klar, aktualisierte Tipps kommen gleich."))
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
         "/jetzt &mdash; sofort eine Nachricht mit allen anstehenden, "
         "aktuell berechneten Tipps schicken\n"
         "/um 09:00 &mdash; einmalige Sendung zu diesem Zeitpunkt\n"
         "/status &mdash; aktuelle Einstellung\n\n"
         "Automatisch kommt sonst: einmal fruehzeitig eine Uebersicht des ganzen "
         "Spieltags, dann pro Spiel nochmal kurz vor Anpfiff.")


def _status(cfg):
    return (f"<b>Automatik:</b> {cfg.get('vorlauf_frueh_stunden', 8.0):g}h vor dem "
            f"ersten Spiel des Spieltags (gebuendelt), dann "
            f"{cfg.get('vorlauf_spaet_stunden', 1.5):g}h vor jedem einzelnen Spiel.\n"
            + (f"<b>Geplant:</b> {cfg['geplant_fuer'][:16].replace('T', ' ')} Uhr"
               if cfg.get("geplant_fuer") else ""))


# ---------------------------------------------------------------- Faelligkeit

def faellige(spiele, cfg, state, jetzt):
    """
    Zwei automatische Stufen, unabhaengig voneinander pro Lauf geprueft:

      fruehzeitig - einmal je Spieltag (Schluessel = Datum des ersten kommenden
      Anstosses), sobald `vorlauf_frueh_stunden` vor diesem ersten Anstoss
      erreicht ist. Enthaelt ALLE Spiele des Fensters (RUNDEN_FENSTER Tage ab
      dem ersten Anstoss) in einer Nachricht.

      spaet - je Spiel, sobald `vorlauf_spaet_stunden` vor dessen eigenem
      Anstoss erreicht ist. Alle Spiele, die im selben Lauf faellig werden,
      kommen zusammen in einer Nachricht.

    Beide Schwellen bleiben erfuellt, bis das jeweilige Spiel anpfeift - ein
    verspaeteter/ausgefallener Cron-Lauf holt eine faellige Nachricht beim
    naechsten Mal einfach nach, nichts geht verloren. Ist der Anpfiff schon
    vorbei, wird fuer dieses Spiel nichts mehr verschickt.
    """
    kommend = [s for s in spiele if s["anstoss"] > jetzt]

    frueh = []
    if kommend:
        erster_anstoss = min(s["anstoss"] for s in kommend)
        runde = erster_anstoss.date().isoformat()
        frueh_gesendet = state.setdefault("frueh_gesendet", {})
        schwelle_frueh = timedelta(hours=float(cfg.get("vorlauf_frueh_stunden", 8.0)))
        if not frueh_gesendet.get(runde) and jetzt >= erster_anstoss - schwelle_frueh:
            grenze = erster_anstoss + RUNDEN_FENSTER
            frueh = [s for s in kommend if s["anstoss"] <= grenze]

    gesendet = state.get("gesendet", {})
    schwelle_spaet = timedelta(hours=float(cfg.get("vorlauf_spaet_stunden", 1.5)))
    spaet = [s for s in kommend
             if not gesendet.get(spiel_id(s)) and (s["anstoss"] - jetzt) <= schwelle_spaet]

    return frueh, spaet, (runde if kommend else None)


# ---------------------------------------------------------------- Hauptlauf

def main():
    argumente = set(sys.argv[1:])
    probe = "--probe" in argumente
    nur_seite = "--nur-seite" in argumente

    cfg = lade(CONFIG, STANDARD_CONFIG)
    state = lade(STATE, {"gesendet": {}, "frueh_gesendet": {}, "telegram_offset": 0})
    jetzt = datetime.now(TZ)
    antworten = []

    if not probe and not nur_seite:
        cfg, state, antworten = verarbeite_befehle(cfg, state)
    if "--jetzt" in argumente:
        cfg["sofort_senden"] = True

    print(f"Lauf {jetzt:%d.%m.%Y %H:%M}")

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

    manuell = bool(cfg.get("sofort_senden"))
    if cfg.get("geplant_fuer"):
        try:
            if jetzt >= datetime.fromisoformat(cfg["geplant_fuer"]):
                manuell = True
        except ValueError:
            cfg["geplant_fuer"] = None

    if manuell:
        anstehend = [s for s in spiele if s["anstoss"] > jetzt]
        frueh, spaet, runde = [], [], None
    else:
        anstehend = []
        frueh, spaet, runde = faellige(spiele, cfg, state, jetzt) if spiele else ([], [], None)

    if probe:
        print(f"\n  Probelauf: manuell={manuell}, fruehzeitig={len(frueh)}, "
              f"kurz-vorher={len(spaet)}. Nichts gesendet, nichts gespeichert.")
    elif nur_seite:
        print("\n  Nur Seite neu geschrieben.")
    else:
        chat = cfg.get("telegram_chat_id")
        for ziel, text in antworten:
            notify.sende(text, ziel)

        if manuell:
            if notify.sende(notify.formatiere(anstehend, "Bundesliga - alle anstehenden Tipps"), chat):
                print(f"\n  {len(anstehend)} Tipps auf Anfrage geschickt.")
            else:
                print("\n  Senden fehlgeschlagen.")
            cfg["sofort_senden"] = False
            cfg["geplant_fuer"] = None
        else:
            if frueh:
                titel = "Bundesliga - Tipps zum Spieltag"
                if notify.sende(notify.formatiere(frueh, titel), chat):
                    state.setdefault("frueh_gesendet", {})[runde] = True
                    print(f"\n  Fruehzeitige Uebersicht geschickt ({len(frueh)} Spiele).")
                else:
                    print("\n  Fruehzeitige Uebersicht fehlgeschlagen - bleibt faellig.")
            if spaet:
                titel = "Bundesliga - Tipps kurz vor Anpfiff"
                if notify.sende(notify.formatiere(spaet, titel), chat):
                    for s in spaet:
                        state.setdefault("gesendet", {})[spiel_id(s)] = True
                    print(f"\n  Tipps kurz vor Anpfiff geschickt ({len(spaet)} Spiele).")
                else:
                    print("\n  Tipps kurz vor Anpfiff fehlgeschlagen - bleiben faellig.")
            if not frueh and not spaet:
                print("\n  Nichts faellig.")

        # abgelaufene Eintraege aufraeumen
        grenze = (jetzt - timedelta(days=14)).date().isoformat()
        state["gesendet"] = {k: v for k, v in state.get("gesendet", {}).items()
                             if k[:10] >= grenze}
        state["frueh_gesendet"] = {k: v for k, v in state.get("frueh_gesendet", {}).items()
                                   if k >= grenze}
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
