from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings


def _get_database_url() -> str:
    url = settings.DATABASE_URL
    # Railway fournit postgres:// mais SQLAlchemy 2.x exige postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


engine = create_engine(
    _get_database_url(),
    pool_pre_ping=True,  # vérifie la connexion avant utilisation
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()