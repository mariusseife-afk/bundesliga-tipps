# Bundesliga Tipp-System (statistischer Kern)

Ziel: maximale Punkte im 3/2/1/0-Tippspiel durch ein backtest-validiertes
Dixon-Coles-Modell + deinen EV-Optimierer. Keine LLM-Schicht im Kern — die kommt
nur dazu, wenn der Backtest zeigt, dass sie Punkte bringt.

## Dateien
- `model.py` — Dixon-Coles mit Zeitgewichtung, liefert volle Score-Matrix.
- `ev_engine.py` — EV-Optimierer (= deine tipp_engine-Logik, nachgerechnet korrekt).
- `data_loader.py` — laedt football-data.co.uk CSVs (Ergebnisse + Quoten).
- `backtest.py` — Walk-Forward-Test gegen Baselines. DER wichtigste Teil.
- `predict.py` — woechentliche Tippausgabe fuer anstehende Spiele.
- `_smoke_test.py` — nur Funktionstest mit Fake-Daten (keine echten Zahlen).

## Schritt 1: Daten holen (machst du, ich komme an die Domain nicht ran)
Lade je eine CSV pro Saison von football-data.co.uk:
- https://www.football-data.co.uk/mmz4281/2122/D1.csv
- https://www.football-data.co.uk/mmz4281/2223/D1.csv
- https://www.football-data.co.uk/mmz4281/2324/D1.csv
- https://www.football-data.co.uk/mmz4281/2425/D1.csv
- https://www.football-data.co.uk/mmz4281/2526/D1.csv  (sobald Saison laeuft)

## Schritt 2: Backtest (die eigentliche Antwort auf "wie viele Punkte")
```python
from data_loader import load_many
from backtest import run

df = load_many(["2122/D1.csv", "2223/D1.csv", "2324/D1.csv", "2425/D1.csv"])

res, summ = run(df, w_market=0.0)     # reines Dixon-Coles
print(summ)                            # Punkte/Spiel je Methode
print(summ * 9)                        # grob pro 9-Spiele-Spieltag
```
Vergleiche dann:
- `model` vs. `konst_1_1` / `konst_2_1` -> schlaegt dein Modell die dummen Baselines?
- `model` vs. `markt_modal` -> schlaegt es die Buchmacher-Tendenz?

Markt-Beimischung testen (Daten entscheiden lassen):
```python
for w in [0.0, 0.3, 0.5, 0.7, 1.0]:
    _, s = run(df, w_market=w)
    print(w, round(s["model"], 4))
```
xi (Zeitgewichtung) tunen:
```python
for xi in [0.0015, 0.0025, 0.004, 0.006]:
    _, s = run(df, xi=xi)
    print(xi, round(s["model"], 4))
```
Den w_market / xi mit den meisten Punkten uebernehmen.

## Schritt 3: Live tippen
```python
from predict import predict
fixtures = [("Bayern Munich", "Dortmund"), ("Leverkusen", "RB Leipzig")]
for h, a, tip, info in predict(df, fixtures, xi=BESTER_XI):
    print(f"{h} - {a}: {tip}  ({info})")
```
Teamnamen exakt wie in der CSV schreiben (z.B. "Bayern Munich", "Ein Frankfurt",
"M'gladbach"). Einmal `df["home"].unique()` ausgeben und die Schreibweisen kopieren.

## Optionaler manueller Eingriff (statt LLM)
In `predict(..., adjust={"Dortmund": 0.85})` skalierst du die Angriffsstaerke
eines Teams, z.B. wenn der Top-Stuermer ausfaellt. NUR einsetzen, wenn du es
vorher im Backtest auf historischen Ausfaellen geprueft hast — sonst fuegst du
nur Rauschen hinzu.

## Gemessene Ergebnisse (Stand August 2026)

Walk-Forward ueber 1129 getippte Spiele, Saisons 21/22 bis 25/26, Modell einmal
je Spieltag neu gefittet:

| Methode | Punkte/9er-Spieltag | exakt | Tendenz |
|---|---|---|---|
| DC-Form + Markt-Raender (xi=0.006, w=1.0) | **7.86** | 10.1% | 54.8% |
| Buchmacher-Favorit -> 2:1/1:1/1:2 | 7.60 | 9.4% | 54.3% |
| reines Dixon-Coles | 7.30 | 9.2% | 50.8% |
| immer 2:1 | 6.13 | 7.9% | 43.6% |
| immer 1:1 | 5.49 | 11.2% | 24.9% |

Einordnung: mit sicher bekanntem Sieger jedes Spiels waeren 16.5 Punkte drin,
mit durchweg exaktem Ergebnis 27.

Wichtigste Erkenntnisse:
- Das Modell schlaegt die konstanten Baselines klar und signifikant (+1.17 bzw.
  +1.81 Punkte/Spieltag, p < 0.001).
- Gegen die blanke Buchmacherquote betraegt der Vorsprung nur +0.26 Punkte/Spieltag
  und ist **pro Spiel nicht signifikant** (p = 0.19). Ueber eine Saison mit 40
  Mitspielern entscheidet er trotzdem: rund 60% Siegchance statt unter 13%.
- Die Exakt-Trefferquote liegt bei rund 10%, nicht bei 13-16%.
- Der EV-Optimierer nutzt nur 10 bis 17 verschiedene Ergebnisse, 84-94% davon
  sind 2:1, 1:2, 1:1, 1:0 und 2:0. Mehr Daten koennen den Tipp nur zwischen
  diesen wenigen Feldern verschieben.

Ohne Zusatznutzen getestet und wieder verworfen:
- Schussdaten statt Tore als Ratinggrundlage: 7.75 (-0.11, n.s.)
- Asian-Handicap-Linie plus Over/Under ohne Teammodell: 7.66 (-0.20, n.s.)

Spaeter tippen bringt dagegen etwas: mit Schlussquoten statt fruehen Quoten
8.07 statt 7.86 Punkte/Spieltag, der Tipp aendert sich bei 10.6% der Spiele.

## Automatischer Betrieb
Siehe `ANLEITUNG.md`. Der Live-Teil liegt in `tippsystem.py`, `run.py`,
`notify.py` und `page.py`.
