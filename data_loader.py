"""
Laedt football-data.co.uk Bundesliga-CSVs (D1.csv).

Download (eine Datei pro Saison), Beispiel-URLs:
    https://www.football-data.co.uk/mmz4281/2324/D1.csv   (Saison 2023/24)
    https://www.football-data.co.uk/mmz4281/2425/D1.csv   (Saison 2024/25)
    https://www.football-data.co.uk/mmz4281/2526/D1.csv   (Saison 2025/26)

Relevante Spalten:
    Date, HomeTeam, AwayTeam, FTHG (Heimtore), FTAG (Auswaertstore)
    Quoten (optional, fuer Markt-Vergleich): AvgH/AvgD/AvgA oder B365H/B365D/B365A
"""

import pandas as pd


def load_csv(path):
    df = pd.read_csv(path, encoding="latin-1")
    out = pd.DataFrame({
        "date": pd.to_datetime(df["Date"], dayfirst=True, errors="coerce"),
        "home": df["HomeTeam"].astype(str).str.strip(),
        "away": df["AwayTeam"].astype(str).str.strip(),
        "hg": pd.to_numeric(df["FTHG"], errors="coerce"),
        "ag": pd.to_numeric(df["FTAG"], errors="coerce"),
    })
    # Marktquoten (Durchschnitt bevorzugt, sonst Bet365)
    for tgt, cols in {"oh": ["AvgH", "B365H"], "od": ["AvgD", "B365D"], "oa": ["AvgA", "B365A"]}.items():
        for c in cols:
            if c in df.columns:
                out[tgt] = pd.to_numeric(df[c], errors="coerce")
                break
    return out.dropna(subset=["date", "home", "away"]).sort_values("date").reset_index(drop=True)


def load_many(paths):
    return pd.concat([load_csv(p) for p in paths], ignore_index=True).sort_values("date").reset_index(drop=True)


def market_probs(row):
    """Wandelt 1X2-Quoten in entschaerfte (margin-bereinigte) Wahrscheinlichkeiten."""
    if "oh" not in row or pd.isna(row.get("oh")):
        return None
    inv = [1 / row["oh"], 1 / row["od"], 1 / row["oa"]]
    s = sum(inv)
    return [x / s for x in inv]  # [P(Heim), P(Remis), P(Auswaerts)]
