"""
Telegram-Anbindung: Tipps verschicken und Befehle entgegennehmen.

Das Bot-Token kommt aus der Umgebungsvariable TELEGRAM_TOKEN, die Chat-ID aus
TELEGRAM_CHAT_ID oder aus der config.json. Beides steht bewusst NICHT im Code.
Token anlegen: in Telegram @BotFather anschreiben, /newbot, Token kopieren.
"""

import json
import os
import urllib.parse
import urllib.request

from tippsystem import formatiere_zeit

API = "https://api.telegram.org/bot{token}/{methode}"


def _token():
    return os.environ.get("TELEGRAM_TOKEN", "").strip()


def aktiv():
    return bool(_token())


def _ruf_auf(methode, **params):
    token = _token()
    if not token:
        return None
    url = API.format(token=token, methode=methode)
    daten = urllib.parse.urlencode(
        {k: v for k, v in params.items() if v is not None}).encode()
    try:
        with urllib.request.urlopen(url, data=daten, timeout=25) as r:
            antwort = json.loads(r.read().decode())
        return antwort if antwort.get("ok") else None
    except Exception as e:
        print(f"  Telegram-Aufruf '{methode}' fehlgeschlagen: {e}")
        return None


def sende(text, chat_id):
    """Schickt eine Nachricht. Gibt True bei Erfolg zurueck."""
    if not chat_id:
        print("  Keine Telegram-Chat-ID gesetzt - Nachricht nicht verschickt.")
        return False
    return _ruf_auf("sendMessage", chat_id=chat_id, text=text,
                    parse_mode="HTML", disable_web_page_preview="true") is not None


def hole_befehle(offset):
    """
    Holt neue Nachrichten an den Bot. Gibt (befehle, neuer_offset) zurueck.
    befehle ist eine Liste von (text, chat_id).
    """
    antwort = _ruf_auf("getUpdates", offset=offset, timeout=0)
    if not antwort:
        return [], offset
    befehle = []
    neuer = offset
    for upd in antwort.get("result", []):
        neuer = max(neuer, upd.get("update_id", 0) + 1)
        nachricht = upd.get("message") or upd.get("edited_message") or {}
        text = (nachricht.get("text") or "").strip()
        chat = (nachricht.get("chat") or {}).get("id")
        if text and chat:
            befehle.append((text, str(chat)))
    return befehle, neuer


def formatiere(spiele, ueberschrift):
    """Baut die Telegram-Nachricht aus einer Tippliste."""
    zeilen = [f"<b>{ueberschrift}</b>", ""]
    for s in spiele:
        if not s.get("tipp"):
            zeilen.append(f"{s['home']} - {s['away']}: kein Tipp ({s.get('hinweis','')})")
            continue
        zeit = formatiere_zeit(s["anstoss"])
        marke = "" if s["quelle"] == "modell+markt" else f"  [{s['quelle']}]"
        zeilen.append(f"<code>{s['tipp']}</code>  {s['home']} - {s['away']}")
        zeilen.append(f"     {zeit} Uhr, EP {s['ep']:.2f}{marke}")
    if spiele:
        ep = [s["ep"] for s in spiele if s.get("ep") is not None]
        if ep:
            zeilen += ["", f"Erwartete Punkte gesamt: <b>{sum(ep):.1f}</b> "
                           f"aus {len(ep)} Spielen"]
    return "\n".join(zeilen)
