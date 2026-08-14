# Prompt fuer Codex

Alles ab der Linie kopieren und an Codex geben.

---

## KONTEXT

Dieses Repository ist ein fertiges Bundesliga-Tippsystem. Es rechnet Tipps fuer
ein Tippspiel mit der Wertung 3 = exaktes Ergebnis, 2 = richtige Tordifferenz,
1 = richtige Tendenz, 0 = falsch, und schickt sie per Telegram.

Der Code ist geschrieben und getestet. **Deine Aufgabe ist das Deployment, nicht
die Weiterentwicklung.** Bring das Ding zum Laufen.

Aufbau:

| Datei | Zweck |
|---|---|
| `tippsystem.py` | Daten holen, Dixon-Coles fitten, Tipps rechnen |
| `run.py` | ein Durchlauf: Telegram-Befehle, Faelligkeit, Versand, Seiten schreiben |
| `notify.py` | Telegram senden und empfangen |
| `page.py` | baut die HTML-Seiten und `tipps.json` |
| `config.json` | Modus, Vorlaufzeiten, `github_repo`, `telegram_bot` |
| `state.json` | welche Tipps schon raus sind |
| `.github/workflows/tipps.yml` | Cronjob alle 10 Minuten |
| `ANLEITUNG.md` | die Einrichtung in Prosa |
| `model.py`, `ev_engine.py`, `backtest.py`, `data_loader.py` | statistischer Kern |

`run.py` schreibt bei jedem Lauf drei Dateien nach `docs/`:

- `tipps.json` — die Tipps als Rohdaten
- `index.html` — Tipps fest eingebaut, fuer GitHub Pages
- `sites.html` — enthaelt keine Tipps, sondern laedt `tipps.json` per `fetch`
  von `raw.githubusercontent.com`. Fuer ChatGPT Sites.

## WICHTIG: EINE LEERE TIPPLISTE IST KEIN FEHLER

Die Saison 2026/27 hat noch nicht begonnen. Die Bundesliga steht deshalb noch
nicht im Vorschau-Feed von football-data.co.uk, und `run.py` meldet
"Keine Bundesligaspiele im Vorschau-Feed". **Das ist der erwartete Zustand.**

Ebenso erwartet: `Saison 2627 nicht verfuegbar (HTTP Error 300)`. Die CSV der
laufenden Saison entsteht erst mit dem ersten Spieltag.

Repariere beides nicht. Baue keine Ersatz-Datenquelle ein. Die Mechanik ist
gegen den Feed getestet, dort stehen aktuell andere Ligen drin, die Bundesliga
kommt mit Saisonstart dazu. Wenn du die Anzeige testen willst, nutze den
Layout-Test weiter unten.

## AUFGABE

Deploye das System vollstaendig, in dieser Reihenfolge. Pruefe nach jedem
Schritt, dass er wirklich funktioniert hat, statt weiterzugehen.

**1. Repository auf GitHub.**
Falls noch kein Remote existiert: anlegen und pushen. Das Repository muss
**oeffentlich** sein, sonst darf die Sites-Seite spaeter `tipps.json` nicht
laden. `state.json` und `config.json` gehoeren mit ins Repository, der Cronjob
schreibt sie zurueck.

**2. Secret hinterlegen.**
Das Telegram-Token gehoert als Repository-Secret `TELEGRAM_TOKEN` hinterlegt.
Das Token erzeuge ich selbst beim BotFather. Frag mich danach, wenn es fehlt.
Schreib es unter keinen Umstaenden in eine Datei.

**3. GitHub Pages einschalten.**
Settings > Pages, Source `Deploy from a branch`, Branch `main`, Ordner `/docs`.
Danach die URL aufrufen und pruefen, dass die Seite erscheint.

**4. Workflow einmal manuell ausloesen.**
Actions > "Bundesliga Tipps" > Run workflow. Pruefe im Log, dass der Lauf
durchlaeuft, die drei Dateien in `docs/` erzeugt und den Stand zurueckcommittet.
Wenn er scheitert, liegt es fast immer an Berechtigungen: der Workflow braucht
`contents: write`, das steht schon drin, aber in manchen Organisationen muss
unter Settings > Actions > General zusaetzlich "Read and write permissions"
gesetzt werden.

**5. `github_repo` eintragen.**
In `config.json` `"github_repo": "benutzername/repository"` setzen, committen,
`python run.py --nur-seite` laufen lassen. Danach steht in `docs/sites.html`
die richtige Datenadresse.

**6. ChatGPT Sites anbinden.**
`docs/sites.html` dort veroeffentlichen. Siehe naechster Abschnitt.

**7. Ende zu Ende pruefen.**
Beide URLs oeffnen (GitHub Pages und ChatGPT Sites) und bestaetigen, dass
Kopfzeile, Steuerungsknoepfe und Fusstext erscheinen. Die Spieltabelle bleibt
bis Saisonstart leer, mit entsprechendem Hinweis — das ist korrekt.

## WAS SCHON GEPRUEFT IST

Diese Punkte sind verifiziert, untersuche sie nicht erneut:

- `raw.githubusercontent.com` liefert `Access-Control-Allow-Origin: *`. Eine
  fremd gehostete Seite darf `tipps.json` also per `fetch` laden.
- Beide HTML-Dateien haben `<meta charset="utf-8">`. Ohne das kamen Umlaute
  und Gedankenstriche kaputt an.
- `sites.html` wurde lokal gegen einen HTTP-Server getestet: Tabelle, Knoepfe,
  Modus-Haken und die Markierung `nur markt` rendern korrekt. Auch die
  Fehlerfaelle (Datenquelle nicht erreichbar, `github_repo` leer) zeigen
  jeweils eine verstaendliche Meldung.
- Die Knoepfe sind Telegram-Deeplinks der Form
  `https://t.me/BOTNAME?start=jetzt`. Das ist Absicht: eine statische Seite
  kann kein Geheimnis speichern, ein Schluessel im Quelltext waere oeffentlich.
- Anstosszeiten im Feed stehen in Londoner Zeit und werden in `tippsystem.py`
  nach Europe/Berlin umgerechnet. Nicht anfassen.

## DIE OFFENE FRAGE BEI SCHRITT 6

Unbekannt ist, ob ChatGPT Sites eigenes JavaScript ausfuehrt. Davon haengt ab,
welcher Weg funktioniert. Finde es empirisch heraus, rate nicht.

Test: Seite veroeffentlichen und oeffnen.
- Inhalt erscheint -> JavaScript laeuft, fertig.
- Dauerhaft "wird geladen ..." -> JavaScript ist blockiert, nimm die Leiter unten.
- Meldung ueber nicht erreichbare Daten -> JavaScript laeuft, aber die Quelle
  stimmt nicht. Pruefe `github_repo` und ob das Repository oeffentlich ist.

Falls JavaScript blockiert ist, arbeite diese Leiter von oben nach unten ab und
nimm die erste Stufe, die wirklich funktioniert. Teste jede Stufe, statt sie
fuer moeglich zu halten.

1. **iframe** — minimale Seite bei ChatGPT Sites, die die GitHub-Pages-URL in
   einem `<iframe>` einbettet. Zeigt live denselben Inhalt.
2. **Weiterleitung** — `<meta http-equiv="refresh">` auf die GitHub-Pages-URL.
3. **Verlinken** — Startseite mit einem grossen Knopf zur GitHub-Pages-Seite.

Wenn keine Stufe funktioniert, sag es klar. Dann bleibt GitHub Pages der
Anzeigeort, und das ist kein Beinbruch.

Wenn du in ChatGPT Sites nicht selbst veroeffentlichen kannst, bereite alles
vor und gib mir eine Klick-fuer-Klick-Anleitung. Sag mir dann klar, dass du es
nicht selbst konntest, statt es als erledigt darzustellen.

## GUARDS

- **Aendere die Modellmethodik nicht.** `model.py`, `ev_engine.py` und die
  Rechenlogik in `tippsystem.py` bleiben unberuehrt. Insbesondere `XI = 0.006`
  und `W_MARKET = 1.0` nicht anfassen — beide stammen aus einem Backtest.
- **Erfinde keine Leistungszahlen.** Die Angaben in `README.md` und im
  Seitenfuss (7,86 Punkte je 9er-Spieltag, 1129 Spiele, rund 10 % exakt)
  stammen aus echten Laeufen. Weder aendern noch neue dazuerfinden.
- **Kein Token in einer Datei.** Weder HTML noch JSON noch Python. Wenn ein Weg
  einen Schluessel in die Seite schreiben wuerde, nimm ihn nicht, sondern sag
  mir warum.
- **Keine neuen Abhaengigkeiten** ueber `requirements.txt` hinaus, keine
  LLM-Schicht, keine zusaetzlichen Datenquellen.
- **Kein Redesign.** Wenn dir am Layout etwas nicht gefaellt, sag es mir,
  aendere es nicht ungefragt.
- `.github/workflows/tipps.yml` nur anfassen, wenn dein Weg es zwingend
  braucht, und dann erklaeren was du geaendert hast.

## LOKAL TESTEN

```bash
python run.py --probe          # rechnet alles, sendet nichts, speichert nichts
python -m http.server 8731 --directory docs
```

Dann `http://localhost:8731/sites.html` oeffnen.

Fuer einen reinen Layout-Test ohne Live-Daten: im erzeugten HTML die
Konstante `URL_JSON` voruebergehend auf `"tipps.json"` setzen, dann liest die
Seite die lokale Datei. Diese Aenderung nicht committen.

## RUECKMELDUNG

Sag mir zum Schluss:

1. Welche Schritte tatsaechlich durchgelaufen sind, und was du dabei geprueft hast.
2. Beide URLs: GitHub Pages und ChatGPT Sites.
3. Welche Stufe bei Schritt 6 funktioniert hat.
4. Was ich noch selbst tun muss.
5. Was nicht funktioniert hat und warum.
