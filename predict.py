"""
Woechentliche Tippausgabe. Trainiert auf allen verfuegbaren Spielen und gibt
fuer eine Liste anstehender Partien den EV-optimalen Tipp aus.

Optionaler manueller Eingriff (statt LLM-Automatik): adjust = {Team: faktor}
verschiebt die Angriffsstaerke eines Teams (z.B. 0.85 wenn Top-Stuermer fehlt).
Erst per Backtest pruefen, ob solche Eingriffe ueberhaupt Punkte bringen.
"""

import numpy as np
from model import DixonColes
from ev_engine import optimal_tip


def predict(df, fixtures, xi=0.0025, adjust=None):
    """
    df: bisherige Saison-/Historiendaten (date, home, away, hg, ag).
    fixtures: Liste von (home, away).
    adjust: optionales Dict {team: angriffsfaktor}, Default 1.0.
    """
    model = DixonColes(xi=xi).fit(df)
    adjust = adjust or {}
    out = []
    for home, away in fixtures:
        m = model.score_matrix(home, away)
        if m is None:
            out.append((home, away, None, "kein Modell (Team unbekannt)"))
            continue
        # einfacher manueller Eingriff: Tor-Masse eines Teams skalieren
        if home in adjust or away in adjust:
            eg = model.expected_goals(home, away)
            if eg:
                lam, mu = eg
                lam *= adjust.get(home, 1.0)
                mu *= adjust.get(away, 1.0)
                g = np.arange(model.max_goals + 1)
                from scipy.stats import poisson
                m = np.outer(poisson.pmf(g, lam), poisson.pmf(g, mu))
                m = m / m.sum()
        a, b, ep = optimal_tip(m)
        out.append((home, away, f"{a}:{b}", f"EV={ep:.3f}"))
    return out


if __name__ == "__main__":
    pass
