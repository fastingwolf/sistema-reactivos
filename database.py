from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine(
    "sqlite:///reactivos.db",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    """Dependencia de FastAPI: abre y cierra una sesión por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()