import re, sys, requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

# ---------- CONFIG ----------
OWN = {"Bionics Buccinasco", "C R A C BIONICS"}
UISP_TEAM = "Bionics Buccinasco"
UISP_TEAMS = ["Bionics Buccinasco", "EDILPLUS Basket Corsico U 13", "Centro Asteria U13",
              "U13 Starsteam BLU", "STARSTEAM U13 M", "NCS CORSICO U13"]
UISP_BASE = "https://gestionalepallacanestro.uisp.it/milano/70/130"
FIP_BASE = "https://fip.it/risultati/"
FIP_PARAMS = {"group": "campionati-regionali", "regione_codice": "LO", "comitato_codice": "RLO",
              "sesso": "M", "codice_campionato": "U13S/M", "codice_fase": "1",
              "codice_girone": "85961"}
FIP_TEAM = "C R A C BIONICS"
# ----------------------------

MESI = {m: i + 1 for i, m in enumerate(
    "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split())}
TZ, UTC = ZoneInfo("Europe/Rome"), ZoneInfo("UTC")
HDR = {"User-Agent": "Mozilla/5.0 (calendario-basket)"}


def titolo(label, home, away):
    h = "Bionics" if home in OWN else home
    a = "Bionics" if away in OWN else away
    return f"🏀 [{label}] {h} - {a}"


def scrape_uisp():
    rx = re.compile(r"(\d{1,2}) ([a-zà]+) (\d{4}) \(\w+\) (\d{2}):(\d{2}) (.+)$", re.I)
    out = {}
    for rnd in (1, 2):
        for n in range(1, 6):
            r = requests.get(UISP_BASE, params={"round": rnd, "roundnumber": n}, headers=HDR, timeout=30)
            r.raise_for_status()
            for a in BeautifulSoup(r.text, "html.parser").select("a[href*='/130/']"):
                txt = " ".join(a.get_text(" ").split())
                if UISP_TEAM not in txt:
                    continue
                m = rx.search(txt)
                if not m:
                    continue
                g, mese, y, hh, mm, venue = m.groups()
                if mese.lower() not in MESI:
                    continue
                start = datetime(int(y), MESI[mese.lower()], int(g), int(hh), int(mm), tzinfo=TZ)
                pre = txt[:m.start()]
                opp = next((t for t in UISP_TEAMS if t != UISP_TEAM and t in pre), "?")
                casa = opp == "?" or pre.find(UISP_TEAM) < pre.find(opp)
                home, away = (UISP_TEAM, opp) if casa else (opp, UISP_TEAM)
                mid = a["href"].rstrip("/").split("/")[-1]
                out[f"uisp-{mid}@basket-u13"] = (start, titolo("UISP", home, away), venue, a["href"])
    return out


def scrape_fip():
    rx = re.compile(
        r"(\d{1,2}) ([A-Za-zà]+) (\d{4}) (\d{2}):(\d{2}) (\d{6}) (.*?)"
        r"Squadra di casa (.+?) Squadra ospite (.+?) Campo di gioco (.+?) 1\S{0,2} Arbitro")
    out = {}
    for ar in ("1", "0"):
        for g in range(1, 6):
            p = dict(FIP_PARAMS, codice_ar=ar, giornata=str(g))
            r = requests.get(FIP_BASE, params=p, headers=HDR, timeout=30)
            r.raise_for_status()
            text = re.sub(r"\s+", " ", BeautifulSoup(r.text, "html.parser").get_text(" "))
            for m in rx.finditer(text):
                d, mese, y, hh, mm, num, _, home, away, venue = m.groups()
                if FIP_TEAM not in (home, away) or mese.lower() not in MESI:
                    continue
                start = datetime(int(y), MESI[mese.lower()], int(d), int(hh), int(mm), tzinfo=TZ)
                out[f"fip-{num}@basket-u13"] = (start, titolo("FIP", home, away), venue, r.url)
    return out


def esc(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")


uisp, fip = scrape_uisp(), scrape_fip()
print("UISP:", len(uisp), "| FIP:", len(fip))
if not uisp or not fip:
    sys.exit("Una fonte non ha restituito partite: file NON aggiornato")

events = {**uisp, **fip}
F = "%Y%m%dT%H%M%SZ"
now = datetime.now(UTC).strftime(F)
out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Basket U13//IT", "CALSCALE:GREGORIAN",
       "X-WR-CALNAME:Basket U13 - Partite", "X-WR-TIMEZONE:Europe/Rome",
       "REFRESH-INTERVAL;VALUE=DURATION:PT3H", "X-PUBLISHED-TTL:PT3H"]
for uid, (st, title, venue, url) in sorted(events.items(), key=lambda x: x[1][0]):
    out += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now}",
            f"DTSTART:{st.astimezone(UTC).strftime(F)}",
            f"DTEND:{(st + timedelta(minutes=90)).astimezone(UTC).strftime(F)}",
            f"SUMMARY:{esc(title)}", f"LOCATION:{esc(venue)}", f"URL:{url}",
            "BEGIN:VALARM", "TRIGGER:-PT90M", "ACTION:DISPLAY", "DESCRIPTION:Partita", "END:VALARM",
            "END:VEVENT"]
out.append("END:VCALENDAR")
open("partite.ics", "w", encoding="utf-8", newline="").write("\r\n".join(out) + "\r\n")
