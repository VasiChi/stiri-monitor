# Monitor Stiri — Universum Events

Script automat de monitorizare a presei de business din Romania.

## Ce face
- Scaneaza 18 surse de stiri zilnic la ora 09:00
- Filtreaza articole relevante pentru industria de events corporate
- Monitorizeaza 63 de companii tinta
- Trimite email zilnic cu rezultatele prioritizate

## Niveluri de prioritate
- COMPANIE TINTA — articol despre o companie din lista ta
- URGENT — 3+ cuvinte cheie intr-un articol
- HOT LEAD — 2 cuvinte cheie intr-un articol

## Setup
pip install -r requirements.txt
export SENDGRID_API_KEY=cheia_ta
python stiri_monitor.py
