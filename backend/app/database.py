from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

# ⚠️ P0 FIX: load_dotenv() MUST run here, NOT just in main.py.
# database.py is imported at module level BEFORE main.py's load_dotenv() executes
# (main.py → from .database import engine, Base → database.py evaluates immediately).
# Without this, DATABASE_URL is None outside Docker, crashing on create_async_engine().
# In Docker, env_file: preloads vars, so this is a harmless no-op.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed — running in Docker where env_file: handles it

DATABASE_URL = os.getenv("DATABASE_URL")

# ⚠️ P0 FIX (REVIEW RECOMMENDATION): Guard against None DATABASE_URL.
# Even with load_dotenv() above, DATABASE_URL can be genuinely missing from .env.
# create_async_engine(None) throws an opaque SQLAlchemy ArgumentError.
# Fail fast with a clear message instead.
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. Check backend/.env or Docker env_file configuration. "
        "Expected format: postgresql+asyncpg://user:pass@host:5432/dbname"
    )

# P2-12 FIX: echo=True floods logs with every SQL statement at 1 req/sec polling.
# Default to False in production. Set SQL_ECHO=true in .env for development debugging.
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
