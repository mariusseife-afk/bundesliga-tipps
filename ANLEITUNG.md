# Einrichtung

## Was das System tut

Alle zehn Minuten: Ergebnisse und Quoten holen, Modell fitten, Tipps rechnen,
faellige Tipps per Telegram schicken, `docs/index.html` neu schreiben.
Kein LLM in der Schleife, keine API-Schluessel ausser dem Telegram-Token, keine Kosten.

## Sofort ausprobieren (ohne alles Weitere)

```bash
python run.py --probe
```

Rechnet alles durch und zeigt es an, verschickt nichts und speichert nichts.

## 1. Telegram-Bot anlegen

Das Token musst du selbst erzeugen, ich fasse keine Zugangsdaten an.

1. In Telegram **@BotFather** anschreiben, `/newbot` senden, Namen vergeben.
2. BotFather antwortet mit einem Token (`123456789:AAF...`). Das ist dein Geheimnis.
3. Den Bot-Namen (ohne `@`) in `config.json` unter `telegram_bot` eintragen.
4. Deinen Bot einmal anschreiben, z.B. `/status`. Beim naechsten Lauf merkt sich
   das System deine Chat-ID automatisch.

Lokal testen:

```bash
set TELEGRAM_TOKEN=dein-token-hier
python run.py --jetzt
```

## 2. Auf GitHub legen

```bash
git init
git add -A
git commit -m "Bundesliga Tippsystem"
git branch -M main
git remote add origin https://github.com/DEINNAME/bundesliga-tipps.git
git push -u origin main
```

Dann im Repository:

- **Settings > Secrets and variables > Actions > New repository secret**
  Name `TELEGRAM_TOKEN`, Wert das Token vom BotFather.
- **Settings > Pages**: Source `Deploy from a branch`, Branch `main`, Ordner `/docs`.
  Die Seite liegt danach unter `https://DEINNAME.github.io/bundesliga-tipps/`.

Ab jetzt laeuft alles von selbst. Unter **Actions** siehst du jeden Lauf.

## 3. Bedienung

Auf der Seite oder direkt im Telegram-Chat:

| Knopf / Befehl | Wirkung |
|---|---|
| **Tipps jetzt senden** / `/jetzt` | schickt sofort alle anstehenden Tipps |
| **5 Stunden vorher** / `/modus standard` | Standard, pro Spiel funf Stunden vorher |
| **Freitag frueh** / `/modus freitag` | alles auf einmal, sobald verfuegbar (72 h) |
| **30 Minuten vorher** / `/modus spaet` | spaetester Stand, Aufstellungen eingepreist |
| `/vorlauf 3` | eigene Vorlaufzeit in Stunden |
| `/um 09:00` | einmalige Sendung zu diesem Zeitpunkt |
| `/status` | aktuelle Einstellung |

Die Knoepfe auf der Seite sind Telegram-Deeplinks. Das ist bewusst so: eine
statische Seite kann kein Geheimnis speichern, ein Schluessel im Quelltext waere
oeffentlich lesbar. Ueber Telegram bleibt das Token dort, wo es hingehoert.

**Wartezeit:** Ein Knopfdruck wirkt beim naechsten Lauf, also innerhalb von etwa
zehn Minuten, unter Last auch mal nach zwanzig. Fuer echten Sofortversand braeuchte
es einen dauerhaft laufenden Dienst statt eines Cronjobs.

## 4. Die Seite bei ChatGPT Sites einhaengen

Es gibt zwei Seiten im Ordner `docs`, fuer zwei verschiedene Zwecke.

**`docs/index.html`** enthaelt die Tipps fest eingebaut. Gut fuer GitHub Pages,
wo sie bei jedem Lauf neu geschrieben wird. Ungeeignet fuer ChatGPT Sites, weil
du sie nach jedem Lauf neu hochladen muesstest.

**`docs/sites.html`** ist die Variante fuer ChatGPT Sites. Sie enthaelt keine
Tipps, sondern holt sie beim Oeffnen selbst aus deinem GitHub-Repository. Du
veroeffentlichst sie **einmal** und sie zeigt trotzdem immer den aktuellen Stand.
Sie aktualisiert sich zusaetzlich alle zwei Minuten und immer dann, wenn du den
Tab wieder in den Vordergrund holst.

Dafuer musst du in `config.json` eintragen, wo die Daten liegen:

```json
"github_repo": "deinname/bundesliga-tipps",
"github_zweig": "main"
```

Danach einmal `python run.py --nur-seite` laufen lassen, dann steht in
`docs/sites.html` die richtige Adresse. Diese Datei bei ChatGPT Sites
veroeffentlichen, fertig.

Das Repository muss dafuer **oeffentlich** sein, sonst darf die Seite die Daten
nicht laden. In `docs/tipps.json` stehen nur Spielpaarungen und Tipps, keine
Zugangsdaten. Das Telegram-Token liegt als GitHub-Secret woanders und taucht
in keiner der beiden Dateien auf.

**Eine Unsicherheit:** Ob ChatGPT Sites eigenes JavaScript ausfuehrt, kann ich
von hier aus nicht pruefen. Falls die Seite dort leer bleibt und nur
&bdquo;wird geladen&ldquo; anzeigt, wird das Skript blockiert. Dann bleibt
GitHub Pages als Anzeigeort; die Adresse dort funktioniert genauso im Browser
und laesst sich als Lesezeichen auf den Startbildschirm legen.

## Was wann passiert

- **Vor Saisonstart** steht die Bundesliga noch nicht im Vorschau-Feed. Das System
  laeuft trotzdem und schreibt eine Seite mit entsprechendem Hinweis.
- **In den ersten Spieltagen** haben Aufsteiger noch keine Historie. Ihre Tipps
  sind mit `nur markt` markiert und kommen allein aus den Quoten. Das ist so
  gewollt und im Backtest die bessere Variante.
- **Fehlt der Quotenanbieter** fuer ein Spiel, wird `nur modell` markiert. Diese
  Tipps sind im Schnitt schwaecher.

## Dateien

| Datei | Zweck |
|---|---|
| `tippsystem.py` | Daten holen, Modell fitten, Tipps rechnen |
| `run.py` | ein Durchlauf: Befehle, Faelligkeit, Versand, Seite |
| `notify.py` | Telegram senden und empfangen |
| `page.py` | HTML-Seite bauen |
| `config.json` | Modus und Vorlaufzeiten (wird vom Bot geaendert) |
| `state.json` | welche Tipps schon raus sind |
| `model.py`, `ev_engine.py`, `backtest.py`, `data_loader.py` | statistischer Kern |

`config.json` und `state.json` werden vom Cronjob zurueck ins Repository
geschrieben. Nicht wundern, wenn dort automatische Commits auftauchen.
