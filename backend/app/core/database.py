from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

from sqlalchemy import text

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.execute(text("RESET ROLE;"))
        except Exception:
            pass
        db.close()
