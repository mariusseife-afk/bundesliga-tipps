"""
Walk-Forward-Backtest. Trainiert das Modell nur auf Spielen VOR dem jeweiligen
Spieltag und tippt dann. Vergleicht den EV-Tipp gegen mehrere Baselines, damit
du siehst, ob dein System ueberhaupt etwas schlaegt.

Aufruf am Ende der Datei (Beispiel) anpassen.
"""

import numpy as np
import pandas as pd

from model import DixonColes
from ev_engine import optimal_tip, points_earned
from data_loader import market_probs


def _region_probs(m):
    n = m.shape[0]
    I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    d = I - J
    return m[d > 0].sum(), m[d == 0].sum(), m[d < 0].sum()  # H, D, A


def blend_with_market(m, mkt, w_market=0.5):
    """Skaliert die DC-Matrix so, dass ihre 1X2-Raender Richtung Markt verschoben werden."""
    if mkt is None:
        return m
    ph, pd_, pa = _region_probs(m)
    th = (1 - w_market) * ph + w_market * mkt[0]
    td = (1 - w_market) * pd_ + w_market * mkt[1]
    ta = (1 - w_market) * pa + w_market * mkt[2]
    n = m.shape[0]
    I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    d = I - J
    out = m.copy()
    out[d > 0] *= th / ph if ph > 0 else 1
    out[d == 0] *= td / pd_ if pd_ > 0 else 1
    out[d < 0] *= ta / pa if pa > 0 else 1
    return out / out.sum()


def market_baseline_tip(mkt):
    """Modal-Score je Markt-Tendenz: Heim->2:1, Remis->1:1, Auswaerts->1:2."""
    if mkt is None:
        return None
    i = int(np.argmax(mkt))
    return [(2, 1), (1, 1), (1, 2)][i]


def run(df, start_after_games=60, xi=0.0025, w_market=0.0, min_team_games=4):
    """
    start_after_games: erst tippen, wenn so viele Spiele Trainingshistorie da sind.
    w_market: 0 = reines DC; >0 = DC mit Markt-Beimischung.
    """
    df = df.dropna(subset=["hg", "ag"]).reset_index(drop=True)
    rows = []
    for k in range(start_after_games, len(df)):
        train = df.iloc[:k]
        test = df.iloc[k]
        # genug Historie fuer beide Teams?
        gh = ((train["home"] == test["home"]) | (train["away"] == test["home"])).sum()
        ga = ((train["home"] == test["away"]) | (train["away"] == test["away"])).sum()
        if gh < min_team_games or ga < min_team_games:
            continue

        model = DixonColes(xi=xi).fit(train, ref_date=test["date"])
        m = model.score_matrix(test["home"], test["away"])
        if m is None:
            continue

        mkt = market_probs(test) if "oh" in df.columns else None
        if w_market > 0 and mkt is not None:
            m = blend_with_market(m, mkt, w_market)

        result = (int(test["hg"]), int(test["ag"]))

        # EV-Tipp aus dem Modell
        a, b, _ = optimal_tip(m)
        pts_model = points_earned((a, b), result)

        # Baselines
        pts_11 = points_earned((1, 1), result)
        pts_21 = points_earned((2, 1), result)
        mb = market_baseline_tip(mkt)
        pts_mkt = points_earned(mb, result) if mb else np.nan

        rows.append({
            "date": test["date"], "home": test["home"], "away": test["away"],
            "result": f"{result[0]}:{result[1]}", "tip": f"{a}:{b}",
            "model": pts_model, "konst_1_1": pts_11, "konst_2_1": pts_21,
            "markt_modal": pts_mkt,
        })

    res = pd.DataFrame(rows)
    summary = res[["model", "konst_1_1", "konst_2_1", "markt_modal"]].mean()
    return res, summary


if __name__ == "__main__":
    # ----- echte Nutzung: CSVs herunterladen, Pfade eintragen -----
    # from data_loader import load_many
    # df = load_many(["2324/D1.csv", "2425/D1.csv", "2526/D1.csv"])
    # res, summ = run(df, w_market=0.0)   # erst reines DC messen
    # print(summ)            # Durchschnittliche Punkte pro Spiel je Methode
    # print(summ * 9)        # grobe Hochrechnung auf einen 9-Spiele-Spieltag
    pass
