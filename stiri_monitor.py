"""
Monitor Stiri Romanesti
"""

import feedparser
import schedule
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from colorama import Fore, init

init(autoreset=True)

RSS_FEEDS = {
    "HotNews":   "https://www.hotnews.ro/rss",
    "G4Media":   "https://www.g4media.ro/feed",
    "Profit.ro": "https://www.profit.ro/rss",
    "ZF":        "https://www.zf.ro/rss",
}

CUVINTE_CHEIE = [
    "evenimente", "eveniment", "corporate",
    "profit", "angajati", "angajat", "angajare", "angajari",
]

ORA_RULARE   = "08:00"
EMAIL_FROM   = "vassich@gmail.com"
EMAIL_TO     = "marian.chirita@universum.ro"
EMAIL_PAROLA = "iovu zngs ywpm jbts"

def contine_cuvant_cheie(text):
    text_lower = text.lower()
    return [kw for kw in CUVINTE_CHEIE if kw in text_lower]

def trimite_email(html_body, total):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Stiri relevante - {datetime.now().strftime('%d %B %Y')} ({total} articole)"
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PAROLA)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print(Fore.GREEN + f"  Email trimis catre {EMAIL_TO}")
    except Exception as e:
        print(Fore.RED + f"  Eroare email: {e}")

def scaneaza_toate_sursele():
    print()
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + f"  STIRI - {datetime.now().strftime('%d %B %Y, %H:%M')}")
    print(Fore.CYAN + "=" * 60)

    total_gasite = 0
    html_sectiuni = []

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
                cuvinte_gasite = contine_cuvant_cheie(f"{titlu} {descriere}")
                if cuvinte_gasite:
                    total_gasite += 1
                    taguri = " ".join([f"<span style='background:#e8f4fd;color:#1a73e8;padding:2px 8px;border-radius:12px;font-size:12px;'>{kw}</span>" for kw in cuvinte_gasite])
                    print(Fore.GREEN + f"\n  {titlu}")
                    print(Fore.WHITE + f"  Tags: {', '.join(cuvinte_gasite)}")
                    print(Fore.WHITE + f"  {link}")
                    articole_html.append(f"""
                        <div style="border-left:3px solid #1a73e8;margin:12px 0;padding:10px 15px;background:#f9f9f9;border-radius:0 8px 8px 0;">
                            <a href="{link}" style="font-size:15px;font-weight:600;color:#111;text-decoration:none;">{titlu}</a><br>
                            <div style="margin:6px 0;">{taguri}</div>
                            <span style="color:#999;font-size:12px;">{data}</span>
                        </div>
                    """)
            if not articole_html:
                print(Fore.WHITE + "  Niciun articol relevant.")
            else:
                html_sectiuni.append(f"<h2 style='color:#333;border-bottom:2px solid #1a73e8;padding-bottom:6px;'>{sursa}</h2>{''.join(articole_html)}")
        except Exception as e:
            print(Fore.RED + f"  Eroare la {sursa}: {e}")

    print()
    print(Fore.CYAN + f"  TOTAL: {total_gasite} articole gasite")
    print(Fore.CYAN + "=" * 60)

    if total_gasite > 0:
        html = f"""<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;padding:20px;">
            <div style="background:#1a73e8;color:white;padding:20px;border-radius:10px;margin-bottom:20px;">
                <h1 style="margin:0;">Monitor Stiri</h1>
                <p style="margin:5px 0 0;">{datetime.now().strftime('%d %B %Y, %H:%M')} &mdash; {total_gasite} articole relevante</p>
            </div>
            {''.join(html_sectiuni)}
            <p style="color:#999;font-size:12px;margin-top:30px;">Cuvinte cheie: {', '.join(CUVINTE_CHEIE)}<br>Surse: {', '.join(RSS_FEEDS.keys())}</p>
        </body></html>"""
        print()
        print(Fore.CYAN + "  Trimit emailul...")
        trimite_email(html, total_gasite)
    else:
        print(Fore.WHITE + "  Niciun articol, emailul nu a fost trimis.")

if __name__ == "__main__":
    print(Fore.CYAN + "\nMonitor pornit!")
    print(f"  Email catre: {EMAIL_TO}")
    print(f"  Rulare zilnica la: {ORA_RULARE}")
    print(Fore.WHITE + "  (Ctrl+C pentru a opri)\n")
    scaneaza_toate_sursele()
    schedule.every().day.at(ORA_RULARE).do(scaneaza_toate_sursele)
    while True:
        schedule.run_pending()
        time.sleep(60)
