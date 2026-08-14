"""
Kern des Tippsystems: Daten holen, Modell fitten, Tipps erzeugen.

Verwendet die im Backtest beste Konfiguration:
    xi = 0.006 (Zeitgewichtung), Markt-Raender erzwungen (w_market = 1.0).

Gemessen im Walk-Forward ueber 1129 Spiele (Saisons 21/22 bis 25/26):
    dieses System                      7.86 Punkte je 9er-Spieltag
    Buchmacher-Favorit -> 2:1/1:1/1:2  7.60
    immer 2:1                          6.13
    immer 1:1                          5.49
Alle Zahlen aus tatsaechlich ausgefuehrten Laeufen, nicht geschaetzt.
"""

import os
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

from model import DixonColes
from ev_engine import optimal_tip
from backtest import blend_with_market, _region_probs

# Im Backtest bester Wert. Nicht ohne neuen Backtest aendern.
XI = 0.006
W_MARKET = 1.0
MAX_GOALS = 8

# football-data.co.uk liefert Anstosszeiten in Londoner Zeit.
TZ_DATEN = ZoneInfo("Europe/London")
TZ_LOKAL = ZoneInfo("Europe/Berlin")

BASIS_URL = "https://www.football-data.co.uk/mmz4281/{saison}/D1.csv"
SPIELPLAN_URL = "https://www.football-data.co.uk/fixtures.csv"
DATEN_ORDNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# ---------------------------------------------------------------- Daten

def saison_code(d):
    """Datum -> Saisoncode von football-data, z.B. 2026-08-20 -> '2627'."""
    jahr = d.year if d.month >= 7 else d.year - 1
    return f"{jahr % 100:02d}{(jahr + 1) % 100:02d}"


def _lade_url(url, ziel, max_alter_stunden=None):
    """Laedt url nach ziel. Ueberspringt, wenn die Datei jung genug ist."""
    if max_alter_stunden is not None and os.path.exists(ziel):
        alter = (datetime.now().timestamp() - os.path.getmtime(ziel)) / 3600
        if alter < max_alter_stunden:
            return ziel
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        inhalt = r.read()
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with open(ziel, "wb") as f:
        f.write(inhalt)
    return ziel


def hole_historie(saisons=None, aktualisiere_laufende=True):
    """
    Laedt die Saison-CSVs (fehlende werden heruntergeladen) und gibt ein
    DataFrame mit date, home, away, hg, ag zurueck.
    """
    heute = datetime.now(TZ_LOKAL).date()
    if saisons is None:
        # laufende Saison plus die fuenf davor
        aktuell = saison_code(heute)
        j = int(aktuell[:2])
        saisons = [f"{(j - k) % 100:02d}{(j - k + 1) % 100:02d}" for k in range(6)][::-1]

    rahmen = []
    for s in saisons:
        pfad = os.path.join(DATEN_ORDNER, f"D1_{s}.csv")
        ist_laufend = s == saison_code(heute)
        try:
            if ist_laufend and aktualisiere_laufende:
                _lade_url(BASIS_URL.format(saison=s), pfad, max_alter_stunden=6)
            elif not os.path.exists(pfad):
                _lade_url(BASIS_URL.format(saison=s), pfad)
        except Exception as e:
            if not os.path.exists(pfad):
                print(f"  Saison {s} nicht verfuegbar ({e}) - uebersprungen")
                continue
            print(f"  Saison {s}: Aktualisierung fehlgeschlagen ({e}), nutze lokale Datei")

        d = pd.read_csv(pfad, encoding="utf-8-sig")
        if "HomeTeam" not in d.columns:
            continue
        rahmen.append(pd.DataFrame({
            "date": pd.to_datetime(d["Date"], dayfirst=True, errors="coerce"),
            "home": d["HomeTeam"].astype(str).str.strip(),
            "away": d["AwayTeam"].astype(str).str.strip(),
            "hg": pd.to_numeric(d["FTHG"], errors="coerce"),
            "ag": pd.to_numeric(d["FTAG"], errors="coerce"),
        }))

    if not rahmen:
        raise RuntimeError("Keine Historiendaten gefunden.")
    df = pd.concat(rahmen, ignore_index=True)
    return (df.dropna(subset=["date", "hg", "ag"])
              .sort_values("date").reset_index(drop=True))


def _spalte(d, namen):
    for n in namen:
        if n in d.columns:
            return pd.to_numeric(d[n], errors="coerce")
    return pd.Series([np.nan] * len(d))


def hole_spielplan(max_alter_stunden=0.4):
    """
    Laedt den Vorschau-Feed und gibt die kommenden Bundesligaspiele zurueck,
    inklusive Quoten. Anstoss wird nach Europe/Berlin umgerechnet.
    """
    pfad = os.path.join(DATEN_ORDNER, "fixtures.csv")
    try:
        _lade_url(SPIELPLAN_URL, pfad, max_alter_stunden=max_alter_stunden)
    except Exception as e:
        print(f"  Spielplan-Download fehlgeschlagen ({e})")
        if not os.path.exists(pfad):
            return pd.DataFrame()

    d = pd.read_csv(pfad, encoding="utf-8-sig")
    if "Div" not in d.columns:
        return pd.DataFrame()
    d = d[d["Div"] == "D1"].copy()
    if d.empty:
        return pd.DataFrame()

    zeit = d["Time"].fillna("15:00").astype(str)
    naiv = pd.to_datetime(d["Date"].astype(str) + " " + zeit,
                          dayfirst=True, errors="coerce")
    anstoss = [None if pd.isna(t) else
               t.tz_localize(TZ_DATEN, ambiguous=True, nonexistent="shift_forward")
                .astimezone(TZ_LOKAL)
               for t in naiv]

    out = pd.DataFrame({
        "anstoss": anstoss,
        "home": d["HomeTeam"].astype(str).str.strip(),
        "away": d["AwayTeam"].astype(str).str.strip(),
        "oh": _spalte(d, ["AvgH", "B365H"]),
        "od": _spalte(d, ["AvgD", "B365D"]),
        "oa": _spalte(d, ["AvgA", "B365A"]),
        "o25": _spalte(d, ["Avg>2.5", "B365>2.5"]),
        "u25": _spalte(d, ["Avg<2.5", "B365<2.5"]),
    })
    return out.dropna(subset=["anstoss"]).sort_values("anstoss").reset_index(drop=True)


# ---------------------------------------------------------------- Markt

def markt_wahrscheinlichkeiten(zeile):
    """1X2-Quoten -> margin-bereinigte Wahrscheinlichkeiten [Heim, Remis, Aus]."""
    q = [zeile.get("oh"), zeile.get("od"), zeile.get("oa")]
    if any(x is None or pd.isna(x) or x <= 1.0 for x in q):
        return None
    inv = np.array([1.0 / x for x in q])
    return inv / inv.sum()


def markt_ueber25(zeile):
    """Over/Under-2.5-Quoten -> P(mehr als 2.5 Tore), oder None."""
    o, u = zeile.get("o25"), zeile.get("u25")
    if o is None or u is None or pd.isna(o) or pd.isna(u) or o <= 1 or u <= 1:
        return None
    inv = np.array([1.0 / o, 1.0 / u])
    return float((inv / inv.sum())[0])


def dc_matrix(lam, mu, rho):
    """Score-Matrix aus zwei Erwartungswerten plus Dixon-Coles-Korrektur."""
    g = np.arange(MAX_GOALS + 1)
    m = np.outer(poisson.pmf(g, lam), poisson.pmf(g, mu))
    m[0, 0] *= 1.0 - lam * mu * rho
    m[0, 1] *= 1.0 + lam * rho
    m[1, 0] *= 1.0 + mu * rho
    m[1, 1] *= 1.0 - rho
    m = np.clip(m, 1e-15, None)
    return m / m.sum()


def _markt_lambdas(p1x2, p_over, rho):
    """
    Sucht (lam, mu), deren Verteilung die Marktwahrscheinlichkeiten trifft.
    Fallback fuer Teams ohne Historie (Aufsteiger am Saisonanfang).
    """
    n = MAX_GOALS + 1
    I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    ist_ueber = (I + J) > 2.5
    ziel = list(p1x2) + ([p_over] if p_over is not None else [])

    def fehler(z):
        lam, mu = np.exp(z)
        m = dc_matrix(lam, mu, rho)
        ist = list(_region_probs(m)) + ([m[ist_ueber].sum()] if p_over is not None else [])
        return float(np.sum((np.array(ist) - np.array(ziel)) ** 2))

    r = minimize(fehler, np.log([1.5, 1.2]), method="Nelder-Mead",
                 options={"xatol": 1e-4, "fatol": 1e-10, "maxiter": 400})
    return tuple(np.exp(r.x))


# ---------------------------------------------------------------- Tipps

def tippe(historie, spiele):
    """
    historie: DataFrame mit date, home, away, hg, ag
    spiele:   DataFrame aus hole_spielplan()

    Gibt eine Liste von Dicts zurueck mit Tipp, Erwartungswert und Herkunft.
    """
    modell = DixonColes(xi=XI).fit(historie)
    rho = float(modell.params[4])
    ergebnis = []

    for zeile in spiele.to_dict("records"):
        heim, aus = zeile["home"], zeile["away"]
        markt = markt_wahrscheinlichkeiten(zeile)
        m = modell.score_matrix(heim, aus)
        quelle = "modell+markt"

        if m is None:
            # mindestens ein Team ohne Historie -> rein aus dem Markt ableiten
            if markt is None:
                ergebnis.append({**zeile, "tipp": None, "ep": None,
                                 "quelle": "keine Daten",
                                 "hinweis": "Team unbekannt und keine Quoten"})
                continue
            lam, mu = _markt_lambdas(markt, markt_ueber25(zeile), rho)
            m = dc_matrix(lam, mu, rho)
            quelle = "nur markt"
        elif markt is not None:
            m = blend_with_market(m, markt, W_MARKET)
        else:
            quelle = "nur modell"

        a, b, ep = optimal_tip(m)
        ph, pd_, pa = _region_probs(m)
        lam, mu = (modell.expected_goals(heim, aus)
                   if modell.expected_goals(heim, aus) else (np.nan, np.nan))
        ergebnis.append({
            **zeile,
            "tipp": f"{a}:{b}", "tipp_h": a, "tipp_a": b,
            "ep": round(float(ep), 3), "quelle": quelle,
            "p_heim": round(float(ph), 3),
            "p_remis": round(float(pd_), 3),
            "p_aus": round(float(pa), 3),
            "p_exakt": round(float(m[a, b]), 3),
            "hinweis": "",
        })
    return ergebnis


WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def formatiere_zeit(t, mit_wochentag=True):
    """Deutsche Kurzform einer Anstosszeit, z.B. 'Sa 22.08. 15:30'."""
    kern = t.strftime("%d.%m. %H:%M")
    return f"{WOCHENTAGE[t.weekday()]} {kern}" if mit_wochentag else kern


def spiel_id(spiel):
    """Stabiler Schluessel je Partie, fuer die Merkliste gesendeter Tipps."""
    t = spiel["anstoss"]
    tag = t.date().isoformat() if hasattr(t, "date") else str(t)[:10]
    return f"{tag}|{spiel['home']}|{spiel['away']}"
