"""
ETL principal — importe Liste_Option_Facturable_ok.csv dans la BDD.
Documents exclus : F24251802 (61 454 € "Gestion" / compte comptable vide).
"""
import os
import sys
from datetime import datetime

import pandas as pd
from dateutil import parser as dateparser
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./resaca.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "csv", "Liste_Option_Facturable_ok.csv")

# Documents exclus du calcul CA (anomalies connues)
EXCLUDED_DOCS = {"F24251802"}  # SCI BON PASTEUR — 61 454,40 € "Gestion", compte vide

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

DDL_LINE_ITEMS = """
CREATE TABLE IF NOT EXISTS line_items (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  reservation_date DATE,
  start_time       TEXT,
  end_time         TEXT,
  duration_min     INTEGER,
  room             TEXT,
  subject          TEXT,
  organizer_id     TEXT,
  civility         TEXT,
  organizer        TEXT,
  option_type      TEXT,
  option_label     TEXT,
  gl_account       TEXT,
  quantity         REAL,
  price_ht         REAL,
  tva_rate         REAL,
  price_ttc        REAL,
  status           TEXT,
  doc_type         TEXT,
  doc_number       TEXT,
  doc_date         DATE
);
"""

DDL_METADATA = """
CREATE TABLE IF NOT EXISTS metadata (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT
);
"""

RENAMES = {
    "Date de réservation":    "reservation_date",
    "Début":                  "start_time",
    "Fin":                    "end_time",
    "Durée":                  "duration_min",
    "Salle":                  "room",
    "Objet":                  "subject",
    "N° de l'organisateur":   "organizer_id",
    "Civilité":               "civility",
    "Organisateur":           "organizer",
    "Type d'option":          "option_type",
    "Option":                 "option_label",
    "Compte comptable":       "gl_account",
    "Quantité":               "quantity",
    "Prix HT":                "price_ht",
    "Taux de TVA":            "tva_rate",
    "Prix TTC":               "price_ttc",
    "Statut":                 "status",
    "Type de document":       "doc_type",
    "N° de document":         "doc_number",
    "Date de document":       "doc_date",
}


def to_date(x):
    if pd.isna(x):
        return None
    try:
        return dateparser.parse(str(x), dayfirst=True).date()
    except Exception:
        return None


def to_time_txt(v):
    if pd.isna(v):
        return None
    try:
        return dateparser.parse(str(v)).strftime("%H:%M:%S")
    except Exception:
        return None


def run():
    print(f"Source : {CSV_PATH}")

    # Lecture
    try:
        df = pd.read_csv(CSV_PATH, encoding="ISO-8859-1", sep=None, engine="python")
    except Exception as e:
        print(f"Erreur lecture CSV : {e}")
        sys.exit(1)
    print(f"  {len(df)} lignes lues")

    # Renommage colonnes
    df = df.rename(columns=RENAMES)

    # Exclusions
    before = len(df)
    df = df[~df["doc_number"].isin(EXCLUDED_DOCS)].copy()
    excluded = before - len(df)
    if excluded:
        print(f"  {excluded} ligne(s) exclue(s) ({EXCLUDED_DOCS})")

    # Dates
    df["reservation_date"] = df["reservation_date"].apply(to_date)
    df["doc_date"]         = df["doc_date"].apply(to_date)

    # Heures
    for col in ["start_time", "end_time"]:
        df[col] = df[col].apply(to_time_txt)

    # Numériques — normalise la notation française (virgule → point)
    for col in ["duration_min", "quantity", "price_ht", "tva_rate", "price_ttc"]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(r"\s", "", regex=True)   # supprime espaces
            .str.replace(",", ".", regex=False)    # virgule → point
            .pipe(pd.to_numeric, errors="coerce")
        )

    # Création tables
    with engine.begin() as conn:
        conn.execute(text(DDL_LINE_ITEMS))
        conn.execute(text(DDL_METADATA))

    # Remplacement complet
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM line_items"))
    print("  Table line_items vidée")

    df.to_sql("line_items", engine, if_exists="append", index=False,
              method="multi", chunksize=200)
    print(f"  {len(df)} lignes insérées")

    # Métadonnées
    now = datetime.now().isoformat(timespec="seconds")
    metadata = {
        "data_source":          os.path.basename(CSV_PATH),
        "data_imported_at":     now,
        "data_excluded_docs":   ",".join(sorted(EXCLUDED_DOCS)),
        "logic_validated_at":   "2026-05-07T00:00:00",
        "logic_version":        "1.0",
        "ca_date_basis":        "reservation_date",
    }
    with engine.begin() as conn:
        for k, v in metadata.items():
            conn.execute(
                text("INSERT OR REPLACE INTO metadata (key, value, updated_at) "
                     "VALUES (:k, :v, :ts)"),
                {"k": k, "v": v, "ts": now},
            )
    print("  Métadonnées enregistrées")
    print(f"\nImport terminé ✅  ({now})")


if __name__ == "__main__":
    run()
