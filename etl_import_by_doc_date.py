import os
import pandas as pd
from sqlalchemy import create_engine, text
from dateutil import parser
from dotenv import load_dotenv

# Chargement de l'URL DATABASE ainsi que le fichier CSV
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CSV_PATH = os.getenv("CSV_PATH")

if not CSV_PATH:
    CSV_PATH = input("Entrez le nom du fichier CSV (ou le chemin complet): ").strip()
    if not CSV_PATH:
        print("❌ Aucun fichier CSV spécifié")
        exit(1)

print("DATABASE_URL IS", DATABASE_URL)
print("CSV_PATH IS", CSV_PATH)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

# Même DDL que l'original
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

def clean_database():
    """Vide complètement la table line_items"""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM line_items"))
        conn.commit()
        print("✅ Table line_items vidée")

def import_csv_filtered_by_doc_date(csv_path, target_month_start, target_month_end):
    """
    Importe le CSV en filtrant par date de document (facturation)
    au lieu de date de réservation
    """
    print(f"📁 Lecture du fichier: {csv_path}")

    try:
        # Lecture du CSV avec gestion des erreurs d'encodage
        try:
            df = pd.read_csv(csv_path, encoding='utf-8', sep=';')
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding='latin-1', sep=';')
        except:
            df = pd.read_csv(csv_path, encoding='cp1252', sep=';')

        print(f"✅ CSV lu: {len(df)} lignes")
        print(f"Colonnes: {list(df.columns)}")

        # Identifier les colonnes de dates (adaptez selon votre CSV)
        date_columns = [col for col in df.columns if 'date' in col.lower() or 'Date' in col]
        print(f"Colonnes de dates détectées: {date_columns}")

        # Conversion des dates
        if 'Date de document' in df.columns:
            df['doc_date_parsed'] = pd.to_datetime(df['Date de document'],
                                                  errors='coerce', dayfirst=True)
            print(f"✅ Utilisation de la colonne: Date de document")
        elif 'Date de création du document' in df.columns:
            df['doc_date_parsed'] = pd.to_datetime(df['Date de création du document'],
                                                  errors='coerce', dayfirst=True)
        elif 'doc_date' in df.columns:
            df['doc_date_parsed'] = pd.to_datetime(df['doc_date'],
                                                  errors='coerce', dayfirst=True)
        else:
            print("❌ Colonne de date de document non trouvée")
            print("Colonnes disponibles:", list(df.columns))
            return

        # Filtrage par date de document
        print(f"📅 Filtrage par date de document: {target_month_start} à {target_month_end}")

        mask = (df['doc_date_parsed'] >= target_month_start) & (df['doc_date_parsed'] < target_month_end)
        df_filtered = df[mask].copy()

        print(f"✅ Après filtrage par date de document: {len(df_filtered)} lignes")

        if len(df_filtered) == 0:
            print("❌ Aucune donnée après filtrage. Vérifiez les dates.")
            return

        # Mapping des colonnes basé sur le CSV réel
        column_mapping = {
            'Date de réservation': 'reservation_date',
            'Début': 'start_time',
            'Fin': 'end_time',
            'Durée': 'duration_min',
            'Salle': 'room',
            'Objet': 'subject',
            "N° de l'organisateur": 'organizer_id',
            'Civilité': 'civility',
            'Organisateur': 'organizer',
            "Type d'option": 'option_type',
            'Option': 'option_label',
            'Compte comptable': 'gl_account',
            'Quantité': 'quantity',
            'Prix HT': 'price_ht',
            'Taux de TVA': 'tva_rate',
            'Prix TTC': 'price_ttc',
            'Statut': 'status',
            'Type de document': 'doc_type',
            'N° de document': 'doc_number',
            'Date de document': 'doc_date'
        }

        # Préparation des données pour l'insertion avec mapping direct
        df_insert = pd.DataFrame()

        # Mapping direct des colonnes essentielles
        mappings_to_apply = {
            'price_ttc': 'Prix TTC',
            'quantity': 'Quantité',
            'status': 'Statut',
            'doc_type': 'Type de document',
            'doc_number': 'N° de document',
            'organizer': 'Organisateur',
            'price_ht': 'Prix HT',
            'tva_rate': 'Taux de TVA',
            'option_label': 'Option',
            'room': 'Salle',
            'subject': 'Objet'
        }

        for target_col, source_col in mappings_to_apply.items():
            if source_col in df_filtered.columns:
                df_insert[target_col] = df_filtered[source_col]
                print(f"✅ Mappé: {source_col} -> {target_col}")
            else:
                print(f"⚠️  Colonne manquante: {source_col}")

        # Dates
        df_insert['doc_date'] = df_filtered['doc_date_parsed'].dt.date

        if 'Date de réservation' in df_filtered.columns:
            df_insert['reservation_date'] = pd.to_datetime(df_filtered['Date de réservation'],
                                                          errors='coerce', dayfirst=True).dt.date

        # Nettoyage et préparation finale
        df_insert = df_insert.dropna(subset=['doc_date', 'price_ttc'])

        print(f"📊 Données prêtes pour insertion: {len(df_insert)} lignes")

        # Insertion en base
        with engine.connect() as conn:
            df_insert.to_sql('line_items', conn, if_exists='append', index=False)
            conn.commit()

        print(f"✅ Import terminé: {len(df_insert)} lignes insérées")

        # Vérification rapide
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) as count FROM line_items")).fetchone()
            print(f"📈 Total en base: {result[0]} lignes")

    except Exception as e:
        print(f"❌ Erreur lors de l'import: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔄 Import ETL filtré par date de document (facturation)")
    print("=" * 60)

    # Création de la table
    with engine.connect() as conn:
        conn.execute(text(DDL))
        conn.commit()

    # Nettoyage de la base
    clean_database()

    # Import pour septembre 2023 (basé sur date de facturation)
    target_start = pd.Timestamp('2023-09-01')
    target_end = pd.Timestamp('2023-10-01')

    import_csv_filtered_by_doc_date(CSV_PATH, target_start, target_end)