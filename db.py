import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./resaca.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine)

def fetch_dataframe(sql: str, params: dict | None = None):
    import pandas as pd
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})

def month_expr(column_name: str) -> str:
    """Retourne l'expression SQL pour tronquer au 1er du mois, selon le dialecte."""
    if engine.dialect.name == "sqlite":
        return f"date(strftime('%Y-%m-01', {column_name}))"
    else:  # postgres
        return f"date_trunc('month', {column_name})::date"


def get_metadata() -> dict:
    """Retourne le contenu de la table metadata sous forme de dict."""
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT key, value, updated_at FROM metadata")).fetchall()
        return {r[0]: {"value": r[1], "updated_at": r[2]} for r in rows}
    except Exception:
        return {}
