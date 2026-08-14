"""
Dixon-Coles Modell mit exponentieller Zeitgewichtung.

Schaetzt Angriffs-/Abwehrstaerke je Team, einen globalen Heimvorteil und die
Dixon-Coles-Korrektur (rho) fuer niedrige Ergebnisse (0:0, 1:0, 0:1, 1:1).
Liefert eine volle Score-Wahrscheinlichkeitsmatrix P(Heim=i, Auswaerts=j),
die direkt in die EV-Engine geht.
"""

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson


def _tau(hg, ag, lam, mu, rho):
    """Dixon-Coles Low-Score-Korrektur (vektorisiert)."""
    out = np.ones_like(lam, dtype=float)
    out = np.where((hg == 0) & (ag == 0), 1.0 - lam * mu * rho, out)
    out = np.where((hg == 0) & (ag == 1), 1.0 + lam * rho, out)
    out = np.where((hg == 1) & (ag == 0), 1.0 + mu * rho, out)
    out = np.where((hg == 1) & (ag == 1), 1.0 - rho, out)
    return out


class DixonColes:
    def __init__(self, xi=0.0025, max_goals=8):
        # xi = Zeitabklingrate pro Tag. 0.0025 -> Halbwertszeit ~277 Tage.
        # Per Backtest tunen (siehe backtest.py).
        self.xi = xi
        self.max_goals = max_goals
        self.teams = None
        self.idx = None
        self.params = None

    def _unpack(self, p, n):
        attack = p[:n]
        defense = p[n:2 * n]
        intercept = p[2 * n]
        home = p[2 * n + 1]
        rho = p[2 * n + 2]
        # Identifizierbarkeit: Angriff/Abwehr auf Mittelwert 0 zentrieren
        attack = attack - attack.mean()
        defense = defense - defense.mean()
        return attack, defense, intercept, home, rho

    def fit(self, df, ref_date=None):
        """
        df: DataFrame mit Spalten date, home, away, hg (Heimtore), ag (Auswaertstore).
        ref_date: Bezugsdatum fuer die Zeitgewichtung (Default: juengstes Spiel).
        """
        df = df.dropna(subset=["hg", "ag"]).copy()
        if ref_date is None:
            ref_date = df["date"].max()
        teams = sorted(set(df["home"]) | set(df["away"]))
        n = len(teams)
        self.teams = teams
        self.idx = {t: i for i, t in enumerate(teams)}

        hi = df["home"].map(self.idx).to_numpy()
        ai = df["away"].map(self.idx).to_numpy()
        hg = df["hg"].to_numpy().astype(int)
        ag = df["ag"].to_numpy().astype(int)
        days = (ref_date - df["date"]).dt.days.to_numpy().astype(float)
        w = np.exp(-self.xi * days)  # Zeitgewichte

        def neg_ll(p):
            attack, defense, intercept, home, rho = self._unpack(p, n)
            log_lam = intercept + attack[hi] - defense[ai] + home
            log_mu = intercept + attack[ai] - defense[hi]
            lam = np.exp(log_lam)
            mu = np.exp(log_mu)
            tau = _tau(hg, ag, lam, mu, rho)
            tau = np.clip(tau, 1e-9, None)  # tau kann bei extremem rho negativ werden
            ll = w * (np.log(tau)
                      + hg * log_lam - lam
                      + ag * log_mu - mu)
            return -ll.sum()

        x0 = np.concatenate([
            np.zeros(n),            # attack
            np.zeros(n),            # defense
            [np.log(1.35)],         # intercept (~ Liga-Tormittel pro Team/Spiel)
            [0.25],                 # home advantage
            [-0.05],                # rho
        ])
        bounds = [(-3, 3)] * (2 * n) + [(-1, 2), (-1, 1), (-0.2, 0.2)]
        res = minimize(neg_ll, x0, method="L-BFGS-B", bounds=bounds)
        self.params = self._unpack(res.x, n)
        return self

    def expected_goals(self, home, away):
        if home not in self.idx or away not in self.idx:
            return None
        attack, defense, intercept, home_adv, rho = self.params
        h, a = self.idx[home], self.idx[away]
        lam = np.exp(intercept + attack[h] - defense[a] + home_adv)
        mu = np.exp(intercept + attack[a] - defense[h])
        return float(lam), float(mu)

    def score_matrix(self, home, away):
        """Volle Wahrscheinlichkeitsmatrix m[i, j] = P(Heim=i, Auswaerts=j)."""
        eg = self.expected_goals(home, away)
        if eg is None:
            return None
        lam, mu = eg
        rho = self.params[4]
        g = np.arange(self.max_goals + 1)
        ph = poisson.pmf(g, lam)
        pa = poisson.pmf(g, mu)
        m = np.outer(ph, pa)
        # DC-Korrektur auf die vier Low-Score-Zellen
        m[0, 0] *= 1.0 - lam * mu * rho
        m[0, 1] *= 1.0 + lam * rho
        m[1, 0] *= 1.0 + mu * rho
        m[1, 1] *= 1.0 - rho
        m = np.clip(m, 0, None)
        return m / m.sum()
