import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medikiosk.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# A remote pooler (Supabase Supavisor) drops idle connections; pre-ping and a
# short recycle keep the first request after a quiet spell from failing.
pool_args = {} if DATABASE_URL.startswith("sqlite") else {"pool_pre_ping": True, "pool_recycle": 280,
                                                         "pool_size": 5, "max_overflow": 5}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    **pool_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
