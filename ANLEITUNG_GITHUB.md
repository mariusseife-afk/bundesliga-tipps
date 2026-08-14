# GitHub einrichten, Schritt fuer Schritt

Rechne mit 20 bis 30 Minuten. Danach laeuft alles von selbst.

Auf deinem Rechner ist Git bereits installiert (Version 2.53) und als Benutzer
`mariusseife-afk` eingetragen. Die GitHub-CLI (`gh`) fehlt, deshalb laeuft alles
ueber die Weboberflaeche. Das ist kein Nachteil.

---

## Schritt 1: Telegram-Bot anlegen

Zuerst, weil du das Token spaeter brauchst.

1. Telegram oeffnen, nach **@BotFather** suchen, Chat starten.
2. `/newbot` senden.
3. Einen Anzeigenamen vergeben, z.B. `Bundesliga Tipps`.
4. Einen Benutzernamen vergeben. Der muss auf `bot` enden, z.B.
   `paul_bundesliga_bot`. Wenn er vergeben ist, probier einen anderen.
5. BotFather antwortet mit einem Token, das so aussieht:
   `8123456789:AAFxyz...`

**Das Token ist ein Passwort.** Es kommt gleich in ein GitHub-Secret und
sonst nirgendwo hin. Nicht in eine Datei, nicht in einen Chat.

Merk dir den **Benutzernamen ohne `@`**, den brauchst du in Schritt 6.

---

## Schritt 2: Repository auf GitHub anlegen

1. Auf [github.com](https://github.com) einloggen.
2. Oben rechts auf **+** > **New repository**.
3. Ausfuellen:
   - **Repository name:** `bundesliga-tipps`
   - **Public** auswaehlen (wichtig, siehe Kasten unten)
   - **Add a README file** NICHT ankreuzen
   - `.gitignore` und `licence` auf `None` lassen
4. **Create repository**.

Auf der naechsten Seite steht eine URL der Form
`https://github.com/mariusseife-afk/bundesliga-tipps.git`. Die brauchst du gleich.

> **Warum oeffentlich?**
> Zwei Gruende. GitHub Pages ist fuer private Repositories kostenpflichtig, und
> deine ChatGPT-Sites-Seite darf `tipps.json` nur laden, wenn sie oeffentlich
> erreichbar ist.
>
> Was oeffentlich waere: der Code, die historischen Spielergebnisse und deine
> Tipps. Keine Zugangsdaten. Das Telegram-Token liegt getrennt davon als
> Secret und ist auch fuer Besucher des Repositories nicht sichtbar.
>
> Wenn du deine Tipps nicht oeffentlich haben willst, sag mir Bescheid, dann
> bauen wir es anders. Beachte aber: deine Mitspieler muessten die Adresse
> erst einmal finden.

---

## Schritt 3: Projekt hochladen

> **Das Lokale ist schon erledigt.** Das Repository ist angelegt, alle Dateien
> sind committet, der Branch heisst `main`, und die Zeilenenden sind auf LF
> normalisiert (sonst waere der Workflow auf Linux gescheitert).
> `git init`, `git add` und `git commit` brauchst du **nicht** mehr.

Terminal im Projektordner oeffnen. Falls du unsicher bist: im Explorer in den
Ordner `Bundesliga Tipps` gehen, Rechtsklick, **Git Bash Here**.

Es fehlen genau zwei Befehle. Erst die Adresse deines Repositories eintragen:

```bash
git remote add origin https://github.com/mariusseife-afk/bundesliga-tipps.git
```

Dann hochladen:

```bash
git push -u origin main
```

> **Diesen Befehl nur ausfuehren, wenn die Adresse oben falsch war.**
> `DEINNAME` und `DEINREPO` sind Platzhalter und muessen ersetzt werden.
> Wenn du ihn versehentlich unveraendert ausfuehrst, zeigt dein Git ins Leere
> und der naechste Push scheitert. Reparatur: denselben Befehl nochmal, dann
> mit der richtigen Adresse.
>
> ```bash
> git remote set-url origin https://github.com/DEINNAME/DEINREPO.git
> ```

Beim Push oeffnet sich ein Browserfenster zur GitHub-Anmeldung.
Einmal bestaetigen, danach merkt sich Windows die Anmeldung.

Wenn stattdessen nach Benutzername und Passwort gefragt wird: dein normales
GitHub-Passwort funktioniert dort nicht mehr. Dann in GitHub unter
**Settings > Developer settings > Personal access tokens > Tokens (classic)**
ein Token mit dem Haken bei `repo` erzeugen und dieses statt des Passworts
eingeben.

Danach die Repository-Seite neu laden. Deine Dateien muessen da sein.

Beim letzten Befehl oeffnet sich ein Browserfenster zur GitHub-Anmeldung.
Einmal bestaetigen, danach merkt sich Windows die Anmeldung.

Wenn stattdessen nach Benutzername und Passwort gefragt wird: dein normales
GitHub-Passwort funktioniert dort nicht mehr. Dann in GitHub unter
**Settings > Developer settings > Personal access tokens > Tokens (classic)**
ein Token mit dem Haken bei `repo` erzeugen und dieses statt des Passworts
eingeben.

Danach die Repository-Seite neu laden. Deine Dateien muessen da sein.

---

## Schritt 4: Actions schreiben lassen

Der Cronjob schreibt seinen Stand ins Repository zurueck. Dafuer braucht er
Schreibrechte.

1. Im Repository auf **Settings**.
2. Links **Actions > General**.
3. Ganz unten bei **Workflow permissions**:
   **Read and write permissions** auswaehlen.
4. **Save**.

Ohne diesen Schritt scheitert jeder Lauf beim Zurueckschreiben.

---

## Schritt 5: Das Token hinterlegen

1. **Settings > Secrets and variables > Actions**.
2. **New repository secret**.
3. **Name:** `TELEGRAM_TOKEN` (exakt so, Grossbuchstaben)
4. **Secret:** das Token vom BotFather aus Schritt 1
5. **Add secret**.

Danach kannst du es selbst nicht mehr auslesen, nur ueberschreiben. Das ist so
gewollt.

---

## Schritt 6: Konfiguration eintragen

Jetzt lokal `config.json` oeffnen und zwei Zeilen ausfuellen:

```json
"telegram_bot": "paul_bundesliga_bot",
"github_repo": "mariusseife-afk/bundesliga-tipps"
```

Bei `telegram_bot` der Benutzername aus Schritt 1, **ohne `@`**.
Bei `github_repo` genau `benutzername/repositoryname`.

Speichern, dann hochladen:

```bash
git add config.json
```

```bash
git commit -m "Bot und Repository eingetragen"
```

```bash
git push
```

---

## Schritt 7: GitHub Pages einschalten

1. **Settings > Pages**.
2. Bei **Source**: `Deploy from a branch`.
3. **Branch:** `main`, Ordner: **`/docs`**.
4. **Save**.

Nach ein bis zwei Minuten ist die Seite erreichbar unter:

```
https://mariusseife-afk.github.io/bundesliga-tipps/
```

Beim ersten Aufruf steht dort noch kein Spiel. Das ist richtig so, die Saison
hat noch nicht begonnen.

---

## Schritt 8: Ersten Lauf ausloesen

1. Oben im Repository auf **Actions**.
2. Falls gefragt wird, ob Workflows laufen duerfen: bestaetigen.
3. Links **Bundesliga Tipps** anklicken.
4. Rechts **Run workflow** > gruener Knopf **Run workflow**.

Nach etwa einer Minute erscheint der Lauf in der Liste. Draufklicken und das
Log ansehen. Es sollte durchlaufen und am Ende entweder Dateien zurueckschreiben
oder "Nichts geaendert" melden.

---

## Schritt 9: Den Bot verbinden

Deinen Bot in Telegram anschreiben und `/status` senden.

Beim naechsten Lauf merkt sich das System deine Chat-ID automatisch und
antwortet dir. Ab da kommen die Tipps bei dir an.

Wenn nach zwanzig Minuten keine Antwort kommt, schau ins Actions-Log.

---

## Fertig. Was ab jetzt passiert

Alle zehn Minuten laeuft der Workflow, holt Ergebnisse und Quoten, rechnet die
Tipps und schreibt die Seite neu. Sobald die Saison beginnt, kommen die Tipps
automatisch fuenf Stunden vor Anpfiff per Telegram.

Umstellen kannst du das jederzeit ueber die Knoepfe auf der Seite oder direkt
im Chat mit `/modus spaet`, `/vorlauf 3`, `/jetzt` oder `/um 09:00`.

---

## Wenn etwas nicht klappt

**`git push` wird abgelehnt, "Permission denied"**
Falscher Account angemeldet. In der Windows-Anmeldeinformationsverwaltung den
Eintrag `git:https://github.com` loeschen und erneut pushen.

**Workflow scheitert bei "Geaenderten Stand zuruecklegen"**
Schritt 4 vergessen oder nicht gespeichert.

**Workflow laeuft, aber keine Telegram-Nachricht**
Drei Moeglichkeiten: Secret heisst nicht exakt `TELEGRAM_TOKEN`, du hast den Bot
noch nie angeschrieben (Schritt 9), oder es ist schlicht nichts faellig, weil
noch keine Spiele anstehen. Das Log sagt dir, welcher Fall vorliegt.

**Pages zeigt 404**
Ordner `/docs` nicht ausgewaehlt, oder die erste Veroeffentlichung laeuft noch.
Zwei Minuten warten und neu laden.

**Der Cronjob laeuft nicht puenktlich**
Das ist normal. GitHub verschiebt geplante Laeufe unter Last um fuenf bis
fuenfzehn Minuten. Fuer den 30-Minuten-Modus ist das knapp, aber es reicht.

**Actions sind nach 60 Tagen ohne Aktivitaet abgeschaltet**
GitHub pausiert Cronjobs in Repositories, in denen lange nichts passiert. Ein
beliebiger Commit weckt sie wieder. In der Saison passiert das nicht.
