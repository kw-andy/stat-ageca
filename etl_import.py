import os
import pandas as pd
from sqlalchemy import create_engine, text
from dateutil import parser
from dotenv import load_dotenv

load_dotenv() #chargement de l'URL DATABASE ainsi que le fichier CSV


print("DATABASE_URL IS", DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

DDL = """
CREATE TABLE IF NOT EXISTS line_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reservation_date DATE,
  start_time TEXT,
  end_time TEXT,
  duration_min INTEGER,
  room TEXT,
  subject TEXT,
  organizer_id TEXT,
  civility TEXT,
  organizer TEXT,
  option_type TEXT,
  option_label TEXT,
  gl_account TEXT,
  quantity REAL,
  price_ht REAL,
  tva_rate REAL,
  price_ttc REAL,
  status TEXT,
  doc_type TEXT,
  doc_number TEXT,
  doc_date DATE
);
"""
with engine.begin() as conn:
    conn.execute(text(DDL))

print("Lecture CSV…")
df = pd.read_csv(CSV_PATH, encoding="ISO-8859-1", sep=None, engine="python")

RENAMES = {
    "Date de réservation": "reservation_date",
    "Début": "start_time",
    "Fin": "end_time",
    "Durée": "duration_min",
    "Salle": "room",
    "Objet": "subject",
    "N° de l'organisateur": "organizer_id",
    "Civilité": "civility",
    "Organisateur": "organizer",
    "Type d'option": "option_type",
    "Option": "option_label",
    "Compte comptable": "gl_account",
    "Quantité": "quantity",
    "Prix HT": "price_ht",
    "Taux de TVA": "tva_rate",
    "Prix TTC": "price_ttc",
    "Statut": "status",
    "Type de document": "doc_type",
    "N° de document": "doc_number",
    "Date de document": "doc_date",
}
df = df.rename(columns=RENAMES)

# Dates
def to_date(x):
    if pd.isna(x): return None
    try: return parser.parse(str(x), dayfirst=True).date()
    except: return None
df["reservation_date"] = df["reservation_date"].apply(to_date)
df["doc_date"] = df["doc_date"].apply(to_date)

# Heures (on garde texte pour SQLite)
def to_time_txt(v):
    if pd.isna(v): return None
    try: return parser.parse(str(v)).strftime("%H:%M:%S")
    except: return None
for c in ["start_time", "end_time"]:
    df[c] = df[c].apply(to_time_txt)

# Numériques
for c in ["duration_min", "quantity", "price_ht", "tva_rate", "price_ttc"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

print("Insertion…")
df.to_sql("line_items", engine, if_exists="append", index=False, method="multi", chunksize=2000)
print("Terminé ✅")
