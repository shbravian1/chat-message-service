from app.models.database import get_engine, get_session_maker
from app.config import get_settings

settings = get_settings()
engine = get_engine(settings.database_url)
SessionLocal = get_session_maker(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()