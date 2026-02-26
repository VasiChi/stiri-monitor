import feedparser
import schedule
import time
import urllib.request
import json
import os
import re
import email.utils
from datetime import datetime, timedelta, timezone
from colorama import Fore, init

init(autoreset=True)

# ── CONFIGURARE ─────────────────────────────────────────────

RSS_FEEDS = {
    "HotNews":         "https://www.hotnews.ro/rss",
    "Profit.ro":       "https://www.profit.ro/rss",
    "ZF":              "https://www.zf.ro/rss",
    "Agerpres":        "https://www.agerpres.ro/rss",
    "Economica":       "https://www.economica.net/rss",
    "Wall-Street.ro":  "https://www.wall-street.ro/rss",
    "Biz.ro":          "https://www.biz.ro/feed",
    "DoingBusiness":   "https://www.doingbusiness.ro/rss",
    "Revista Cariere": "https://revistacariere.ro/feed/",
    "Start-up.ro":     "https://www.start-up.ro/feed/",
    "Business Review": "https://business-review.eu/feed",
    "iQads":           "https://www.iqads.ro/rss",
    "EventMarket":     "https://www.eventmarket.ro/feed",
    "Puls.ro":         "https://www.puls.ro/rss",
    "Reuters":         "https://feeds.reuters.com/reuters/businessNews",
    "Bloomberg":       "https://feeds.bloomberg.com/markets/news.rss",
    "CNN Business":    "http://rss.cnn.com/rss/money_news_international.rss",
    "MarketWatch":     "http://feeds.marketwatch.com/marketwatch/topstories",
}

CUVINTE_CHEIE = {
    "event triggers": [
        "aniversare", "anniversary", "rebranding", "inaugurare", "deschidere",
        "lansare", "launch", "kick-off", "offsite", "gala", "awards",
        "petrecere", "party", "cocktail", "networking", "conferinta", "conference",
        "summit", "congres", "workshop", "seminar", "eveniment", "event",
        "company day", "zi corporativa", "teambuilding", "team building",
        "incentive", "retreat", "reuniune", "ziua companiei", "premiere",
    ],
    "growth signals": [
        "runda de finantare", "serie A", "serie B", "unicorn",
        "capital social", "profit record", "buget de investitii",
        "finantare", "investitie", "investment", "extindere", "expansion",
        "achizitie", "acquisition", "fuziune", "merge",
        "sediu nou", "birou nou", "inchiriere birouri", "relocare",
        "spatiu de lucru", "hub", "angajare", "angajari", "recrutare",
    ],
    "hr focus": [
        "employer branding", "retentia angajatilor", "retentie", "wellbeing",
        "engagement", "cultura organizationala", "hibrid", "remote",
        "beneficii extra-salariale", "reducere turnover", "experiential",
        "Chief People Officer", "HR Director", "Country Manager", "Head of Talent",
    ],
    "corporate": [
        "corporate", "companie", "companii", "afaceri",
        "profit", "venituri", "rezultate", "campanie", "campaign",
    ],
}

BLACKLIST = [
    "guvern", "parlament", "minister", "ministru", "presedinte", "premier",
    "partid", "PSD", "PNL", "USR", "AUR", "coalitie", "opozitie",
    "trafic", "accident", "incendiu", "cutremur", "inundatie",
    "tribunal", "dosar penal", "arest", "retinere", "condamnat",
    "razboi", "conflict", "militar", "armata",
]

COMPANII_TINTA = [
    # IT & Tehnologie
    "Oracle", "Endava", "Microsoft", "IBM", "Bitdefender", "Adobe", "UiPath",
    "Luxoft", "Cognizant", "Amazon", "NXP", "Dell", "Stefanini", "Google",
    # Banking & Financiar
    "Banca Transilvania", "BCR", "BRD", "ING", "Raiffeisen", "CEC Bank",
    "UniCredit", "Alpha Bank", "OTP Bank", "Garanti", "Libra Bank",
    "Allianz", "Groupama", "NN Asigurari",
    # Retail & FMCG
    "Kaufland", "Lidl", "Carrefour", "Profi", "Mega Image", "Dedeman",
    "eMAG", "Coca-Cola", "PepsiCo", "Heineken", "Ursus", "Nestle",
    "Unilever", "Philip Morris", "JTI",
    # Energie & Industrie
    "Petrom", "Romgaz", "Hidroelectrica", "Nuclearelectrica", "Rompetrol",
    "Electrica", "E.ON", "Engie", "Transelectrica", "Transgaz", "Mol",
    "Lukoil", "Liberty", "Alro", "Tenaris",
    # Automotive & Productie
    "Dacia", "Renault", "Ford", "Pirelli", "Michelin", "Autoliv",
    "Hella", "Schaeffler", "Bosch", "Arctic", "Yazaki", "Draexlmaier", "Lear",
    "Continental",
]

TOATE_CUVINTELE  = [kw for lista in CUVINTE_CHEIE.values() for kw in lista]
URGENT_THRESHOLD = 3
HOT_THRESHOLD    = 2
ORA_RULARE       = "07:00"
ISTORIC_FILE     = "istoric_linkuri.json"
EMAIL_FROM       = "vassich@gmail.com"
EMAIL_TO         = "marian.chirita@universum.ro"
SENDGRID_APIKEY  = os.environ.get("SENDGRID_API_KEY", "")

# ── ISTORIC ──────────────────────────────────────────────────

def incarca_istoric():
    if not os.path.exists(ISTORIC_FILE):
        return {}
    try:
        with open(ISTORIC_FILE, "r") as f:
            data = json.load(f)
        limita = datetime.now(timezone.utc) - timedelta(hours=48)
        curatate = {k: v for k, v in data.items()
                    if datetime.fromisoformat(v) > limita}
        eliminate = len(data) - len(curatate)
        if eliminate > 0:
            print(Fore.WHITE + f"  Istoric: {eliminate} linkuri vechi eliminate, {len(curatate)} active.")
        return curatate
    except Exception as e:
        print(Fore.YELLOW + f"  Avertisment: istoric corupt, resetat. ({e})")
        return {}

def salveaza_istoric(istoric):
    try:
        with open(ISTORIC_FILE, "w") as f:
            json.dump(istoric, f)
    except Exception as e:
        print(Fore.RED + f"  Eroare salvare istoric: {e}")

# ── FILTRARE ─────────────────────────────────────────────────

def este_blacklisted(text):
    text_lower = text.lower()
    return any(re.search(rf'\b{re.escape(kw.lower())}\b', text_lower) for kw in BLACKLIST)

def contine_cuvant_cheie(text):
    text_lower = text.lower()
    return [kw for kw in TOATE_CUVINTELE
            if re.search(rf'\b{re.escape(kw.lower())}\b', text_lower)]

def contine_companie_tinta(text):
    text_lower = text.lower()
    return [c for c in COMPANII_TINTA
            if re.search(rf'\b{re.escape(c.lower())}\b', text_lower)]

def este_recent(data_str):
    if not data_str:
        return False
    try:
        data = email.utils.parsedate_to_datetime(data_str)
        if data.tzinfo is None:
            data = data.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - data < timedelta(hours=24)
    except:
        return False

# ── EMAIL ────────────────────────────────────────────────────

def trimite_email(html_body, total, urgent, hot, companii):
    try:
        if companii > 0:
            subject = f"🎯 {companii} COMPANIE TINTA | 🚨 {urgent} urgente | Stiri {datetime.now().strftime('%d %B %Y')}"
        elif urgent > 0:
            subject = f"🚨 URGENT - {urgent} lead-uri fierbinti | Stiri {datetime.now().strftime('%d %B %Y')} ({total} articole)"
        elif hot > 0:
            subject = f"🔥 {hot} HOT LEAD-uri | Stiri {datetime.now().strftime('%d %B %Y')} ({total} articole)"
        else:
            subject = f"Stiri relevante - {datetime.now().strftime('%d %B %Y')} ({total} articole)"

        data = json.dumps({
            "personalizations": [{"to": [{"email": EMAIL_TO}]}],
            "from": {"email": EMAIL_FROM},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}]
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=data,
            headers={
                "Authorization": f"Bearer {SENDGRID_APIKEY}",
                "Content-Type": "application/json"
            }
        )
        urllib.request.urlopen(req)
        print(Fore.GREEN + f"  Email trimis catre {EMAIL_TO}")
    except Exception as e:
        print(Fore.RED + f"  Eroare email: {e}")

# ── SCANARE ──────────────────────────────────────────────────

def scaneaza_toate_sursele():
    print()
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + f"  STIRI - {datetime.now().strftime('%d %B %Y, %H:%M')}")
    print(Fore.CYAN + "=" * 60)

    istoric        = incarca_istoric()
    total_gasite   = 0
    urgent_count   = 0
    hot_count      = 0
    companii_count = 0
    html_companii  = []
    html_urgente   = []
    html_sectiuni  = []

    for sursa, url in RSS_FEEDS.items():
        print()
        print(Fore.YELLOW + f"  {sursa}")
        print(Fore.YELLOW + "-" * 40)
        try:
            feed = feedparser.parse(url)
            articole_html = []
            for entry in feed.entries:
                titlu     = entry.get("title", "")
                descriere = entry.get("summary", "")
                link      = entry.get("link", "")
                data      = entry.get("published", "")

                if link in istoric:
                    continue
                if not este_recent(data):
                    continue
                if este_blacklisted(f"{titlu} {descriere}"):
                    continue

                istoric[link] = datetime.now(timezone.utc).isoformat()

                companii_gasite = contine_companie_tinta(f"{titlu} {descriere}")
                cuvinte_gasite  = contine_cuvant_cheie(f"{titlu} {descriere}")

                if not cuvinte_gasite and not companii_gasite:
                    continue

                total_gasite += 1
                scor      = len(cuvinte_gasite)
                is_target = len(companii_gasite) > 0
                is_urgent = scor >= URGENT_THRESHOLD and not is_target
                is_hot    = scor >= HOT_THRESHOLD and not is_urgent and not is_target

                if is_target:
                    companii_count += 1
                elif is_urgent:
                    urgent_count += 1
                elif is_hot:
                    hot_count += 1

                taguri = " ".join([
                    f"<span style='background:#e8f4fd;color:#1a73e8;padding:2px 8px;border-radius:12px;font-size:12px;'>{kw}</span>"
                    for kw in cuvinte_gasite
                ])
                if companii_gasite:
                    taguri += " " + " ".join([
                        f"<span style='background:#1a1a1a;color:white;padding:2px 8px;border-radius:12px;font-size:12px;'>🎯 {c}</span>"
                        for c in companii_gasite
                    ])

                if is_target:
                    badge = "<span style='background:#6600cc;color:white;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:bold;margin-left:8px;'>🎯 COMPANIE TINTA</span>"
                    border_color = "#6600cc"
                    bg_color = "#f5f0ff"
                    print(Fore.MAGENTA + f"\n  🎯 COMPANIE TINTA: {titlu}")
                elif is_urgent:
                    badge = "<span style='background:#cc0000;color:white;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:bold;margin-left:8px;'>🚨 URGENT</span>"
                    border_color = "#cc0000"
                    bg_color = "#fff0f0"
                    print(Fore.RED + f"\n  🚨 URGENT: {titlu}")
                elif is_hot:
                    badge = "<span style='background:#ff6600;color:white;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:bold;margin-left:8px;'>🔥 HOT LEAD</span>"
                    border_color = "#ff6600"
                    bg_color = "#fff5ee"
                    print(Fore.YELLOW + f"\n  🔥 HOT: {titlu}")
                else:
                    badge = ""
                    border_color = "#1a73e8"
                    bg_color = "#f9f9f9"
                    print(Fore.GREEN + f"\n  {titlu}")

                print(Fore.WHITE + f"  Tags: {', '.join(cuvinte_gasite)}")
                print(Fore.WHITE + f"  {link}")

                card = f"""
                    <div style="border-left:3px solid {border_color};margin:12px 0;padding:10px 15px;background:{bg_color};border-radius:0 8px 8px 0;">
                        <a href="{link}" style="font-size:15px;font-weight:600;color:#111;text-decoration:none;">{titlu}</a>{badge}<br>
                        <div style="margin:6px 0;">{taguri}</div>
                        <span style="color:#999;font-size:12px;">📅 {data} &nbsp;|&nbsp; {sursa}</span>
                    </div>
                """

                if is_target:
                    html_companii.append(card)
                elif is_urgent:
                    html_urgente.append(card)
                else:
                    articole_html.append(card)

            if articole_html:
                html_sectiuni.append(f"<h2 style='color:#333;border-bottom:2px solid #1a73e8;padding-bottom:6px;'>{sursa}</h2>{''.join(articole_html)}")
            else:
                print(Fore.WHITE + "  Niciun articol relevant.")

        except Exception as e:
            print(Fore.RED + f"  Eroare la {sursa}: {e}")

    salveaza_istoric(istoric)

    print()
    print(Fore.CYAN + f"  TOTAL: {total_gasite} | 🎯 {companii_count} TINTA | 🚨 {urgent_count} URGENTE | 🔥 {hot_count} HOT")
    print(Fore.CYAN + "=" * 60)

    if total_gasite > 0:
        companii_section = f"""
            <div style="background:#f5f0ff;border:2px solid #6600cc;border-radius:10px;padding:20px;margin-bottom:25px;">
                <h2 style="color:#6600cc;margin-top:0;">🎯 COMPANII TINTA — Suna acum!</h2>
                {''.join(html_companii)}
            </div>
        """ if html_companii else ""

        urgent_section = f"""
            <div style="background:#fff0f0;border:2px solid #cc0000;border-radius:10px;padding:20px;margin-bottom:25px;">
                <h2 style="color:#cc0000;margin-top:0;">🚨 URGENTE — Contacteaza azi!</h2>
                {''.join(html_urgente)}
            </div>
        """ if html_urgente else ""

        banner = f"""
            <div style="background:#333;color:white;padding:12px 20px;border-radius:8px;margin-bottom:20px;">
                🎯 {companii_count} companii tinta &nbsp;|&nbsp; 🚨 {urgent_count} urgente &nbsp;|&nbsp; 🔥 {hot_count} hot leads
            </div>
        """ if (companii_count + urgent_count + hot_count) > 0 else ""

        html = f"""<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;padding:20px;">
            <div style="background:#1a73e8;color:white;padding:20px;border-radius:10px;margin-bottom:20px;">
                <h1 style="margin:0;">Monitor Stiri — Universum</h1>
                <p style="margin:5px 0 0;">{datetime.now().strftime('%d %B %Y, %H:%M')} &mdash; {total_gasite} articole din ultimele 24h</p>
            </div>
            {banner}
            {companii_section}
            {urgent_section}
            {''.join(html_sectiuni)}
            <p style="color:#999;font-size:12px;margin-top:30px;">Surse: {', '.join(RSS_FEEDS.keys())}</p>
        </body></html>"""

        print()
        print(Fore.CYAN + "  Trimit emailul...")
        trimite_email(html, total_gasite, urgent_count, hot_count, companii_count)
    else:
        print(Fore.WHITE + "  Niciun articol nou, emailul nu a fost trimis.")

# ── MAIN ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print(Fore.CYAN + "\nMonitor pornit — Universum!")
    print(f"  {len(RSS_FEEDS)} surse monitorizate")
    print(f"  {len(COMPANII_TINTA)} companii tinta")
    print(f"  Email catre: {EMAIL_TO}")
    print(f"  Rulare zilnica la: {ORA_RULARE}")
    print(Fore.WHITE + "  (Ctrl+C pentru a opri)\n")
    scaneaza_toate_sursele()
    schedule.every().day.at(ORA_RULARE).do(scaneaza_toate_sursele)
    while True:
        schedule.run_pending()
        time.sleep(60)
