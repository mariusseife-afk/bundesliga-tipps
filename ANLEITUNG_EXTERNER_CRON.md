# Zuverlaessiger externer Trigger, Schritt fuer Schritt

Rechne mit 10 Minuten. Danach laeuft der Workflow zuverlaessig alle paar
Minuten, unabhaengig von GitHubs eigenem (nachweislich unzuverlaessigem)
`schedule`-Trigger.

**Warum ueberhaupt.** GitHub startet `schedule`-Cronjobs auf oeffentlichen
Repos nicht verlaesslich - gemessen (24.08.-04.09.2026, 100 Laeufe): Median
88 statt eingestellter 15 Minuten, groesste Luecke 819 Minuten (13,6 Stunden).
Das laesst sich nicht wegkonfigurieren. Die einzige zuverlaessige Loesung:
ein externer Dienst ruft den Workflow stattdessen selbst per GitHub-API auf.

Der Workflow (`.github/workflows/tipps.yml`) ist bereits vorbereitet und
nimmt jetzt zusaetzlich zum bisherigen `schedule`-Trigger auch
`repository_dispatch`-Aufrufe an (Event-Typ `tipp-lauf`). Fehlen nur noch
zwei Dinge, die ich nicht fuer dich anlegen kann: ein Token und ein Account
bei einem externen Cron-Dienst.

---

## Schritt 1: GitHub Personal-Access-Token erstellen

1. Auf [github.com](https://github.com) einloggen, oben rechts aufs
   Profilbild > **Settings**.
2. Ganz unten links: **Developer settings**.
3. **Personal access tokens** > **Fine-grained tokens** > **Generate new token**.
4. Ausfuellen:
   - **Token name:** z.B. `bundesliga-tipps-cron`
   - **Expiration:** z.B. 1 Jahr (danach musst du ein neues erzeugen und im
     Cron-Dienst eintragen - kein Beinbruch, nur eine Erinnerung wert)
   - **Repository access:** **Only select repositories** ->
     `mariusseife-afk/bundesliga-tipps`
   - **Permissions** > **Repository permissions** > **Actions** ->
     **Read and write** (das ist die einzige Berechtigung, die dieses Token
     braucht)
5. **Generate token**. GitHub zeigt den Token jetzt genau **einmal** an -
   kopieren und irgendwo sicher zwischenspeichern (z.B. Passwort-Manager).

**Das Token ist ein Passwort fuer dieses eine Repository.** Es kommt gleich
in die Konfiguration des Cron-Dienstes und sonst nirgendwo hin.

---

## Schritt 2: Account bei einem externen Cron-Dienst anlegen

Empfehlung: [cron-job.org](https://cron-job.org) (kostenlos, kein Zahlungsmittel
noetig). Registrieren, E-Mail bestaetigen.

---

## Schritt 3: Cronjob anlegen

Im cron-job.org-Dashboard **Create cronjob**:

- **Title:** `Bundesliga Tipps Trigger`
- **URL:**
  `https://api.github.com/repos/mariusseife-afk/bundesliga-tipps/dispatches`
- **Request method:** `POST`
- **Schedule:** alle 5 Minuten (`*/5 * * * *`)
- **Headers** (unter "Advanced" bzw. "Common"):
  - `Authorization: Bearer DEIN_TOKEN_AUS_SCHRITT_1`
  - `Accept: application/vnd.github+json`
  - `Content-Type: application/json`
- **Request body:**
  ```json
  {"event_type": "tipp-lauf"}
  ```

Speichern.

---

## Schritt 4: Testen

1. Im cron-job.org-Dashboard den Job oeffnen und **Run now** / **Execute**
   klicken (nicht auf den naechsten planmaessigen Lauf warten).
2. Auf GitHub in **Actions** pruefen, ob ein neuer Lauf mit dem Ereignis
   `repository_dispatch` erscheint (nicht `schedule`) und erfolgreich
   durchlaeuft.
3. Wenn er fehlschlaegt: meistens liegt es an der `Authorization`-Kopfzeile
   (Tippfehler, abgelaufenes Token) oder daran, dass beim Token in Schritt 1
   nicht **Actions: Read and write** ausgewaehlt wurde.

Ab jetzt laufen zwei Trigger parallel: GitHubs eigener `schedule` (weiterhin
alle 15 Minuten, als kostenloses Backup) und der neue, zuverlaessige
`repository_dispatch` alle 5 Minuten von cron-job.org. Verpasst der eine mal
einen Lauf, faengt der andere es normalerweise auf.
