"""
EV-Optimierer (entspricht deiner punktwert_optimaler_tipp aus tipp_engine.py).

Punktesystem: 3 = exakt, 2 = richtige Tordifferenz, 1 = richtige Tendenz, 0 = falsch.
Da die Stufen verschachtelt sind (exakt c Tordiff c Tendenz), gilt:
    EP(tipp) = P(exakt) + P(gleiche Tordiff) + P(gleiche Tendenz)
Das ist exakt der korrekte Erwartungswert der tiered Wertung. Maximiert wird ueber
alle Kandidaten-Ergebnisse (a, b).
"""

import numpy as np


def _tendency(a, b):
    return 1 if a > b else (-1 if a < b else 0)


def ev_of_tip(m, a, b):
    """Erwartete Punkte fuer Tipp (a, b) gegeben Score-Matrix m."""
    n = m.shape[0]
    I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    diff = I - J
    sign = np.sign(diff)

    p_exact = m[a, b] if (a < n and b < n) else 0.0
    p_diff = m[diff == (a - b)].sum()
    p_tend = m[sign == _tendency(a, b)].sum()
    return p_exact + p_diff + p_tend


def optimal_tip(m, max_tip_goals=6):
    """Gibt (a, b, EP, details) mit maximalem Erwartungswert zurueck."""
    best = None
    for a in range(max_tip_goals + 1):
        for b in range(max_tip_goals + 1):
            ep = ev_of_tip(m, a, b)
            if best is None or ep > best[2]:
                best = (a, b, ep)
    a, b, ep = best
    return a, b, ep


def points_earned(tip, result):
    """Tatsaechlich erzielte Punkte (zur Backtest-Auswertung)."""
    ta, tb = tip
    ra, rb = result
    if (ta, tb) == (ra, rb):
        return 3
    if (ta - tb) == (ra - rb):
        return 2
    if _tendency(ta, tb) == _tendency(ra, rb):
        return 1
    return 0
