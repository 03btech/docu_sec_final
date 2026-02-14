from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
import os
import logging
from pathlib import Path

# ============================================
# Load .env FIRST — before any os.getenv() calls
# ============================================
# In Docker, env_file: is loaded before the process starts, so this is a no-op.
# Outside Docker (local dev, tests), this loads backend/.env so all env vars resolve.
from dotenv import load_dotenv
load_dotenv()

from .database import engine, Base
from .routers import auth, admin, documents, dashboard, security
from .rate_limit import limiter

# ============================================
# Centralized logging configuration
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ============================================
# Module-level SECRET_KEY with sentinel default
# ============================================
_INSECURE_DEFAULT_KEY = "INSECURE-DEV-KEY-DO-NOT-USE-IN-PROD"
SECRET_KEY = os.getenv("SECRET_KEY", _INSECURE_DEFAULT_KEY)
if SECRET_KEY == _INSECURE_DEFAULT_KEY:
    logger.warning(
        "⚠️  SECRET_KEY not set — using insecure default. "
        "This is acceptable for tests but MUST be set in production. "
        "Run build_docker.ps1 or set SECRET_KEY in backend/.env"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # === Startup ===

    # P0 FIX: Validate SECRET_KEY in production
    env = os.getenv("ENVIRONMENT", "production")
    if env != "test" and SECRET_KEY == _INSECURE_DEFAULT_KEY:
        logger.error(
            "FATAL: SECRET_KEY is the insecure default in a non-test environment! "
            "Set SECRET_KEY in backend/.env before deploying."
        )
        raise RuntimeError("SECRET_KEY not configured for production")

    async with engine.begin() as conn:
        # Create any new tables that don't exist yet
        await conn.run_sync(Base.metadata.create_all)
        # Add new columns if they don't exist (idempotent, safe on every startup)
        # ⚠️ SYNC: Enum values must match ClassificationStatus in models.py exactly.
        # NOTE: asyncpg requires each statement to be executed separately.
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE classificationstatus AS ENUM ('queued','extracting_text','classifying','completed','failed');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        await conn.execute(text(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS classification_status classificationstatus DEFAULT 'queued';"
        ))
        await conn.execute(text(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS classification_error VARCHAR(500);"
        ))
        await conn.execute(text(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS classification_queued_at TIMESTAMPTZ;"
        ))

        # P2-REVIEW-16: Index on classification_status for admin retry / stale recovery queries
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_documents_classification_status
            ON documents (classification_status);
        """))

        # Preserve access logs when documents are deleted (audit trail)
        await conn.execute(text(
            "ALTER TABLE access_logs ADD COLUMN IF NOT EXISTS document_name VARCHAR(255);"
        ))
        await conn.execute(text(
            "ALTER TABLE access_logs ALTER COLUMN document_id DROP NOT NULL;"
        ))
        # Change FK cascade from CASCADE to SET NULL
        await conn.execute(text("""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = 'access_logs_document_id_fkey'
                    AND table_name = 'access_logs'
                ) THEN
                    ALTER TABLE access_logs DROP CONSTRAINT access_logs_document_id_fkey;
                    ALTER TABLE access_logs
                        ADD CONSTRAINT access_logs_document_id_fkey
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL;
                END IF;
            END $$;
        """))
        # Backfill document_name for existing access logs that don't have it
        await conn.execute(text("""
            UPDATE access_logs
            SET document_name = d.filename
            FROM documents d
            WHERE access_logs.document_id = d.id
              AND access_logs.document_name IS NULL;
        """))

        # Security logs: add image_data column for camera capture evidence
        await conn.execute(text(
            "ALTER TABLE security_logs ADD COLUMN IF NOT EXISTS image_data TEXT;"
        ))

    # Verify Vertex AI credentials on startup (fail-fast for misconfigurations)
    # P2-15 FIX: Synchronous call — lifespan blocks requests until yield anyway
    try:
        from ml.vertex_ai_classifier import _get_model
        _get_model()
        logger.info("Vertex AI connection verified")
    except Exception as e:
        logger.error(f"Vertex AI initialization failed: {e}")
        # Don't crash — allow the app to start but log prominently

    # Recover stale documents stuck in non-terminal states
    # P2-10 FIX: Split timeouts — active states (10 min) vs queued (30 min)
    ACTIVE_STALE_TIMEOUT_MINUTES = 10
    QUEUED_STALE_TIMEOUT_MINUTES = 30
    try:
        async with engine.begin() as conn:
            # Reset actively-processing docs stuck for >10 min
            await conn.execute(
                text("""
                    UPDATE documents
                    SET classification_status = 'failed',
                        classification_error = 'Classification interrupted (server restart). Retry to reclassify.'
                    WHERE classification_status IN ('extracting_text', 'classifying')
                      AND classification_queued_at < NOW() - INTERVAL '1 minute' * :timeout_minutes
                """),
                {"timeout_minutes": ACTIVE_STALE_TIMEOUT_MINUTES}
            )
            # Reset queued docs stuck for >30 min (likely orphaned)
            await conn.execute(
                text("""
                    UPDATE documents
                    SET classification_status = 'failed',
                        classification_error = 'Document was queued for over 30 minutes without processing. Retry to reclassify.'
                    WHERE classification_status = 'queued'
                      AND classification_queued_at < NOW() - INTERVAL '1 minute' * :timeout_minutes
                """),
                {"timeout_minutes": QUEUED_STALE_TIMEOUT_MINUTES}
            )
            # Fallback: catch documents with NULL classification_queued_at using upload_date
            await conn.execute(
                text("""
                    UPDATE documents
                    SET classification_status = 'failed',
                        classification_error = 'Classification interrupted (server restart). Retry to reclassify.'
                    WHERE classification_status IN ('extracting_text', 'classifying', 'queued')
                      AND classification_queued_at IS NULL
                      AND upload_date < NOW() - INTERVAL '1 minute' * :timeout_minutes
                """),
                {"timeout_minutes": ACTIVE_STALE_TIMEOUT_MINUTES}
            )
        logger.info("Recovered stale in-progress documents (if any)")
    except Exception as e:
        logger.warning(f"Stale document recovery failed (non-fatal): {e}")

    # Ensure upload directory exists (moved from module-level to lifespan)
    # P2-REVIEW-19: PermissionError guard
    upload_dir = os.getenv("UPLOAD_DIR", "/app/uploaded_files")
    try:
        Path(upload_dir).mkdir(exist_ok=True)
    except PermissionError:
        logger.error(
            f"Cannot create upload directory '{upload_dir}': permission denied. "
            f"Check Docker volume mount permissions or UPLOAD_DIR env var."
        )
        raise

    yield
    # === Shutdown ===


app = FastAPI(lifespan=lifespan)

# ⚠️ P0-REVIEW-2: SessionMiddleware MUST be added AFTER app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Rate limiter registration
app.state.limiter = limiter


def _custom_rate_limit_handler(request, exc):
    """P1-REVIEW-9: Custom handler (not private _rate_limit_exceeded_handler)."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."}
    )


app.add_exception_handler(RateLimitExceeded, _custom_rate_limit_handler)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(documents.router, tags=["documents"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(security.router, tags=["security"])


@app.get("/")
async def root():
    return {"message": "Document Security API"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker Compose healthcheck.

    P2-REVIEW-17: Includes lightweight DB connectivity probe (SELECT 1)."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "db": "unreachable"}
        )
