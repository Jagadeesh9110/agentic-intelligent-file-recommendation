from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import settings


class Base(DeclarativeBase):
    metadata = MetaData(schema="ai")


engine = create_engine(settings.ai_database_url, pool_pre_ping=True)
session_factory = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Generator[Session]:
    with session_factory() as session:
        yield session


def check_database_connection() -> bool:
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
    return True
