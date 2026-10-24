import io, re, sys, requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from pypdf import PdfReader

# ---------- CONFIG ----------
OWN = {"Bionics Buccinasco", "C R A C BIONICS"}
UISP_TEAM = "Bionics Buccinasco"
UISP_TEAMS = ["Bionics Buccinasco", "EDILPLUS Basket Corsico U 13", "Centro Asteria U13",
              "U13 Starsteam BLU", "STARSTEAM U13 M", "NCS CORSICO U13"]
UISP_BASE = "https://gestionalepallacanestro.uisp.it/milano/70/130"

FIP_PDF = "https://backend.fip.it/api/v1/calendario.pdf"
FIP_PARAMS = {"comitato_codice": "RLO", "regione_codice": "LO", "sesso": "M",
              "codice_campionato": "U13S/M", "codice_fase": "1", "codice_girone": "85961",
              "codice_andata_ritorno": "1", "giornata": "1"}
FIP_TEAM = "C R A C BIONICS"
FIP_TEAMS = ["URANIA MILANO", "ARMANI OLIMPIA MILANO", "C R A C BIONICS",
             "CITTA' DI OPERA", "EBRO MILANO"]
# ----------------------------

MESI = {m: i + 1 for i, m in enumerate(
    "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split())}
TZ, UTC = ZoneInfo("Europe/Rome"), ZoneInfo("UTC")
HDR = {"User-Agent": "Mozilla/5.0 (calendario-basket)"}


def titolo(label, home, away):
    def nome(n):
        if n in OWN:
            return "Bionics"
        return n.title() if label == "FIP" else n
    return f"🏀 [{label}] {nome(home)} - {nome(away)}"


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
    r = requests.get(FIP_PDF, params=FIP_PARAMS, headers=HDR, timeout=60)
    r.raise_for_status()
    text = " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    text = re.sub(r"\s+", " ", text)
    t = "|".join(re.escape(x) for x in sorted(FIP_TEAMS, key=len, reverse=True))
    rx = re.compile(
        rf"(\d{{6}}) ({t}) ({t}) (\d{{2}})/(\d{{2}})/(\d{{2}}) - (\d{{2}}):(\d{{2}}) (.+?)"
        r"(?= \d{6} | \d Giornata| pag\. \d+ di \d+|$)")
    out = {}
    for m in rx.finditer(text):
        num, home, away, d, mo, y, hh, mm, venue = m.groups()
        if FIP_TEAM not in (home, away):
            continue
        start = datetime(2000 + int(y), int(mo), int(d), int(hh), int(mm), tzinfo=TZ)
        out[f"fip-{num}@basket-u13"] = (start, titolo("FIP", home, away), venue.strip(), r.url)
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
