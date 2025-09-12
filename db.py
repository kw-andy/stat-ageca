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
        # 'YYYY-MM-01' via strftime()
        return f"date(strftime('%Y-%m-01', {column_name}))"
    else:  # postgres
        return f"date_trunc('month', {column_name})::date"
