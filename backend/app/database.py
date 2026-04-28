from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from .config import settings


SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{settings.db_file.as_posix()}"
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"timeout": 15},
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-16000")  # 16 MB
    cursor.execute("PRAGMA foreign_keys=ON")     # enforce FK constraints
    cursor.close()


SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
# Alias kept for backwards-compat with any code that imports by this name.
AsyncSessionLocal = SessionLocal
Base = declarative_base()


async def get_db():
    async with SessionLocal() as db:
        yield db
