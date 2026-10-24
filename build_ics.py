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
UISP_SITE = "https://gestionalepallacanestro.uisp.it"
UISP_BASE = UISP_SITE + "/milano/70/130"

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
    rx
