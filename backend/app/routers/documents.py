import asyncio
import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from ..database import async_session, get_db
from .. import crud, models, schemas
from ..dependencies import get_current_user
from ..rate_limit import limiter
from ml.classifier import extract_document_text_async, classify_extracted_text_async

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploaded_files"))

# Daily upload quota per user (cost guardrail for Gemini API calls)
MAX_UPLOADS_PER_USER_PER_DAY = int(os.getenv("MAX_UPLOADS_PER_USER_PER_DAY", "50"))

# Maximum file size in bytes (default 100MB)
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100")) * 1024 * 1024

async def _update_status(db: AsyncSession, doc_id: int, status, error=None):
    """Update classification_status atomically. Rolls back on failure (P1-REVIEW-7)."""
    try:
        await db.execute(
            update(models.Document)
            .where(models.Document.id == doc_id)
            .values(
                classification_status=status,
                classification_error=error,
            )
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


def _sanitize_classification_error(exc: Exception) -> str:
    """Map exception types to safe user-facing messages (P0-REVIEW-6)."""
    error_type = type(exc).__name__
    SAFE_ERROR_MAP = {
        "Unauthenticated": "Authentication error — contact your administrator.",
        "PermissionDenied": "Service account lacks required permissions — contact admin.",
        "ResourceExhausted": "Classification service temporarily busy — retry later.",
        "InvalidArgument": "Document could not be processed by the classification service.",
        "DeadlineExceeded": "Classification timed out — retry later.",
        "ServiceUnavailable": "Classification service temporarily unavailable — retry later.",
        "InternalServerError": "Classification service encountered an internal error — retry later.",
        "ValueError": str(exc)[:500],
        "RuntimeError": "Classification configuration error — contact your administrator.",
    }
    return SAFE_ERROR_MAP.get(
        error_type,
        f"Classification failed ({error_type}). Contact admin if this persists.",
    )


async def classify_document_pipeline(doc_id: int, file_path: str):
    """Background pipeline: extract text → classify via Vertex AI, with status updates.

    Creates its own AsyncSession (request-scoped session is closed by the time
    BackgroundTasks run). Uses atomic CAS to prevent duplicate pipelines.
    """
    run_id = uuid4().hex[:8]
    logger.info("[run=%s] Starting pipeline for doc %d: %s", run_id, doc_id, file_path)

    async with async_session() as db:
        try:
            # Atomic CAS: queued → extracting_text (prevents duplicate pipelines)
            cas_result = await db.execute(
                update(models.Document)
                .where(
                    models.Document.id == doc_id,
                    models.Document.classification_status == models.ClassificationStatus.queued,
                )
                .values(
                    classification_status=models.ClassificationStatus.extracting_text,
                    classification_error=None,
                    classification_queued_at=func.now(),
                )
            )
            await db.commit()
            if cas_result.rowcount == 0:
                logger.info("[run=%s] Doc %d: already past 'queued', skipping", run_id, doc_id)
                return

            # Stage 1: Text extraction
            text_or_chunks = await extract_document_text_async(file_path)
            if not text_or_chunks:
                logger.warning("[run=%s] No text extracted from %s", run_id, file_path)
                await _update_status(
                    db, doc_id, models.ClassificationStatus.failed,
                    error="No text could be extracted from the document",
                )
                return

            # Stage 2: Gemini classification
            await _update_status(db, doc_id, models.ClassificationStatus.classifying)
            classification_str = await classify_extracted_text_async(text_or_chunks, file_path)

            # Stage 3: Done
            classification = models.ClassificationLevel(classification_str)
            result = await db.execute(
                select(models.Document).where(models.Document.id == doc_id)
            )
            document = result.scalars().first()
            if document:
                document.classification = classification
                document.classification_status = models.ClassificationStatus.completed
                if classification == models.ClassificationLevel.unclassified:
                    document.classification_error = (
                        "Low confidence — Gemini could not determine a classification. "
                        "Manual review recommended."
                    )
                else:
                    document.classification_error = None
                await db.commit()

        except asyncio.CancelledError:
            logger.warning("[run=%s] Pipeline cancelled for doc %d (shutdown?)", run_id, doc_id)
            try:
                async with async_session() as cancel_db:
                    await _update_status(
                        cancel_db, doc_id, models.ClassificationStatus.failed,
                        error="Classification interrupted (server shutdown)",
                    )
            except Exception:
                pass
            raise

        except Exception as e:
            logger.error("[run=%s] Pipeline failed for doc %d: %s", run_id, doc_id, e)
            safe_error = _sanitize_classification_error(e)
            try:
                async with async_session() as error_db:
                    await _update_status(
                        error_db, doc_id, models.ClassificationStatus.failed,
                        error=safe_error,
                    )
            except Exception as status_err:
                logger.error("Failed to update error status for doc %d: %s", doc_id, status_err)


async def cleanup_orphaned_files():
    """Utility function to clean up files that exist in volume but not in database."""
    try:
        existing_files: set[str] = set()
        if UPLOAD_DIR.exists():
            for fp in UPLOAD_DIR.iterdir():
                if fp.is_file():
                    existing_files.add(str(fp))

        async with async_session() as db:
            result = await db.execute(select(models.Document.file_path))
            db_file_paths = set(row[0] for row in result.fetchall())

        orphaned_files = existing_files - db_file_paths

        deleted_count = 0
        for fp in orphaned_files:
            try:
                os.remove(fp)
                deleted_count += 1
            except Exception as e:
                logger.warning("Could not delete orphaned file %s: %s", fp, e)

        return {"deleted_count": deleted_count, "orphaned_files": list(orphaned_files)}
    except Exception as e:
        logger.error("Error during cleanup: %s", e)
        return {"error": str(e)}

@router.post("/upload", response_model=schemas.Document)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Validate file type
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Pre-check file size (UploadFile.size may be None for streaming uploads)
    if file.size is not None and file.size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file.size / (1024*1024):.1f}MB). Maximum: {MAX_UPLOAD_SIZE_BYTES / (1024*1024):.0f}MB",
        )

    # Daily upload quota (P2-REVIEW-15: exclude failed docs from count)
    count_result = await db.execute(
        select(func.count(models.Document.id)).where(
            models.Document.owner_id == current_user.id,
            models.Document.upload_date >= func.now() - text("INTERVAL '1 day'"),
            models.Document.classification_status != models.ClassificationStatus.failed,
        )
    )
    uploads_today = count_result.scalar() or 0
    if uploads_today >= MAX_UPLOADS_PER_USER_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=f"Daily upload limit reached ({MAX_UPLOADS_PER_USER_PER_DAY}). Try again tomorrow.",
        )

    # Save file with UUID prefix to prevent collisions
    safe_filename = f"{current_user.id}_{uuid4().hex[:8]}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    total_bytes = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large (>{MAX_UPLOAD_SIZE_BYTES / (1024*1024):.0f}MB). Upload rejected.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Create document record with 'queued' status
    doc_data = schemas.DocumentCreate(
        filename=file.filename,
        classification=models.ClassificationLevel.unclassified,
    )
    document = await crud.create_document(db, doc_data, current_user.id, str(file_path))

    # Kick off background classification
    background_tasks.add_task(classify_document_pipeline, document.id, str(file_path))

    return document

@router.get("/documents", response_model=list[schemas.Document])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    documents = await crud.get_documents_for_user(db, current_user)
    return documents

@router.get("/documents/shared-with-me", response_model=list[schemas.Document])
async def list_shared_documents(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    documents = await crud.get_shared_documents_for_user(db, current_user.id)
    return documents

@router.get("/documents/owned-by-me", response_model=list[schemas.Document])
async def list_owned_documents(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    documents = await crud.get_documents_by_owner(db, current_user.id)
    return documents

@router.get("/documents/department", response_model=list[schemas.Document])
async def list_department_documents(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.department_id:
        return []
    documents = await crud.get_department_documents(db, current_user.department_id, current_user.id)
    return documents

@router.get("/documents/{doc_id}/classification-status",
            response_model=schemas.ClassificationStatusResponse)
@limiter.limit("2/second")
async def get_classification_status(
    request: Request,
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Document).where(models.Document.id == doc_id)
    )
    document = result.scalars().first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the document owner can check classification status")

    return {
        "doc_id": doc_id,
        "status": document.classification_status,
        "classification": (
            document.classification
            if document.classification_status == models.ClassificationStatus.completed
            else None
        ),
        "error": document.classification_error,
    }


@router.get("/documents/view/{doc_id}")
async def view_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """View document - returns file content for secure viewing only."""
    allowed, reason = await crud.authorize_document_action(db, doc_id, current_user, 'view')

    if not allowed:
        logger.debug("View DENIED for doc %d by user %s: %s", doc_id, current_user.username, reason)
        raise HTTPException(status_code=403, detail=reason)
    
    document = await crud.get_document(db, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = document.file_path
    
    if not os.path.exists(file_path):
        logger.debug("File not found on disk for doc %d: %s", doc_id, file_path)
        raise HTTPException(status_code=404, detail="File not found on server")

    logger.debug("View GRANTED for doc %d (%s) to user %s", doc_id, document.filename, current_user.username)
    
    # Log view access
    await crud.create_access_log(db, schemas.AccessLogCreate(
        document_id=doc_id,
        user_id=current_user.id,
        action='view'
    ))

    # Return file for viewing (not downloading)
    return FileResponse(
        path=file_path, 
        filename=document.filename,
        media_type='application/octet-stream'
    )

@router.get("/documents/download/{doc_id}")
async def download_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    document = await crud.get_document(db, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Basic access check
    can_access = await crud.user_can_access_document(db, current_user.id, doc_id)
    if not can_access:
        raise HTTPException(status_code=403, detail="Not authorized to access this document")

    file_path = document.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    # Log download access
    await crud.create_access_log(db, schemas.AccessLogCreate(
        document_id=doc_id,
        user_id=current_user.id,
        action='download'
    ))

    return FileResponse(path=file_path, filename=document.filename)

@router.get("/documents/{doc_id}", response_model=schemas.Document)
async def get_document_details(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    allowed, reason = await crud.authorize_document_action(db, doc_id, current_user, 'view')
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    result = await db.execute(select(models.Document).where(models.Document.id == doc_id))
    document = result.scalars().first()

    # Log access
    await crud.create_access_log(db, schemas.AccessLogCreate(
        document_id=doc_id,
        user_id=current_user.id,
        action='view'
    ))

    return document

@router.put("/documents/{doc_id}", response_model=schemas.Document)
async def update_document(
    doc_id: int,
    document_update: schemas.DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    allowed, reason = await crud.authorize_document_action(db, doc_id, current_user, 'edit')
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    result = await db.execute(select(models.Document).where(models.Document.id == doc_id))
    document = result.scalars().first()

    # Update fields
    document.filename = document_update.filename
    document.classification = document_update.classification

    await db.commit()
    await db.refresh(document)

    # Log
    await crud.create_access_log(db, schemas.AccessLogCreate(
        document_id=doc_id,
        user_id=current_user.id,
        action='edit_metadata'
    ))

    return document

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    allowed, reason = await crud.authorize_document_action(db, doc_id, current_user, 'delete')
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    # Get document to access file path before deletion
    result = await db.execute(select(models.Document).where(models.Document.id == doc_id))
    document = result.scalars().first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = document.file_path

    # Log the delete action BEFORE deleting (so document_id reference is valid)
    await crud.create_access_log(db, schemas.AccessLogCreate(
        document_id=doc_id,
        user_id=current_user.id,
        action='delete'
    ))

    success, _ = await crud.delete_document(db, doc_id, current_user)
    if not success:
        raise HTTPException(status_code=403, detail="Delete failed")

    # Delete the actual file from the filesystem
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        # Log the error but don't fail the delete operation
        logger.warning("Could not delete file %s: %s", file_path, e)

    return {"message": "Document deleted"}

@router.post("/admin/cleanup-orphaned-files")
async def cleanup_orphaned_files_endpoint(
    current_user: models.User = Depends(get_current_user)
):
    """Admin endpoint to clean up orphaned files (files without database records)."""
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await cleanup_orphaned_files()
    return result

@router.post("/documents/{doc_id}/share", response_model=schemas.DocumentPermission)
async def share_document(
    doc_id: int,
    permission: schemas.DocumentPermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    success, result = await crud.share_document(db, doc_id, permission, current_user)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    
    # Log the sharing action
    await crud.create_access_log(db, schemas.AccessLogCreate(
        document_id=doc_id,
        user_id=current_user.id,
        action=f'share_with_user_{permission.user_id}'
    ))
    
    return result

@router.get("/documents/{doc_id}/permissions", response_model=list[schemas.DocumentPermissionWithUser])
async def get_document_permissions(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all users who have access to this document (owner only)."""
    permissions = await crud.get_document_permissions(db, doc_id, current_user)
    if permissions is False:
        raise HTTPException(status_code=403, detail="Only owner can view permissions")
    return permissions

@router.delete("/documents/{doc_id}/permissions/{permission_id}")
async def revoke_permission(
    doc_id: int,
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Revoke a user's permission to access a document (owner only)."""
    success, message = await crud.revoke_document_permission(db, doc_id, permission_id, current_user)
    if not success:
        raise HTTPException(status_code=403, detail=message)
    
    # Log the revocation
    await crud.create_access_log(db, schemas.AccessLogCreate(
        document_id=doc_id,
        user_id=current_user.id,
        action=f'revoke_permission_{permission_id}'
    ))
    
    return {"message": "Permission revoked successfully"}

@router.put("/documents/{doc_id}/permissions/{permission_id}")
async def update_permission(
    doc_id: int,
    permission_id: int,
    permission_level: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update a user's permission level (owner only)."""
    success, message = await crud.update_document_permission(db, doc_id, permission_id, permission_level, current_user)
    if not success:
        raise HTTPException(status_code=403, detail=message)
    
    # Log the update
    await crud.create_access_log(db, schemas.AccessLogCreate(
        document_id=doc_id,
        user_id=current_user.id,
        action=f'update_permission_{permission_id}_to_{permission_level}'
    ))
    
    return {"message": "Permission updated successfully"}


# ---------------------------------------------------------------------------
# Retry endpoints
# ---------------------------------------------------------------------------

MAX_RETRY_BATCH_SIZE = int(os.getenv("MAX_RETRY_BATCH_SIZE", "20"))


@router.post("/admin/retry-failed-classifications")
async def retry_failed_classifications(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Admin endpoint: retry all documents stuck in 'failed' classification status."""
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(models.Document).where(
            models.Document.classification_status == models.ClassificationStatus.failed
        )
    )
    failed_docs = result.scalars().all()

    if not failed_docs:
        return {"message": "No failed classifications to retry", "count": 0}

    queued_count = 0
    skipped_missing: list[dict] = []
    for doc in failed_docs:
        if queued_count >= MAX_RETRY_BATCH_SIZE:
            break

        if not os.path.exists(doc.file_path):
            skipped_missing.append({"id": doc.id, "file_path": doc.file_path})
            doc.classification_error = "File not found on disk — cannot retry"
            continue

        cas_result = await db.execute(
            update(models.Document)
            .where(
                models.Document.id == doc.id,
                models.Document.classification_status == models.ClassificationStatus.failed,
            )
            .values(
                classification_status=models.ClassificationStatus.queued,
                classification_error=None,
            )
        )
        if cas_result.rowcount > 0:
            background_tasks.add_task(classify_document_pipeline, doc.id, doc.file_path)
            queued_count += 1

    await db.commit()

    remaining = len(failed_docs) - queued_count - len(skipped_missing)
    resp: dict = {"message": f"Retrying {queued_count} failed classifications", "count": queued_count}
    if remaining > 0:
        resp["remaining"] = remaining
        resp["note"] = f"{remaining} documents remain in failed state. Call this endpoint again to retry the next batch."
    if skipped_missing:
        resp["skipped_missing_files"] = skipped_missing
    return resp


@router.post("/documents/{doc_id}/retry-classification")
async def retry_document_classification(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Owner endpoint: retry classification for a single failed document."""
    result = await db.execute(
        select(models.Document).where(models.Document.id == doc_id)
    )
    document = result.scalars().first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the document owner can retry classification")

    if document.classification_status != models.ClassificationStatus.failed:
        raise HTTPException(status_code=400, detail="Only failed classifications can be retried")

    cas_result = await db.execute(
        update(models.Document)
        .where(
            models.Document.id == doc_id,
            models.Document.classification_status == models.ClassificationStatus.failed,
        )
        .values(
            classification_status=models.ClassificationStatus.queued,
            classification_error=None,
        )
    )
    await db.commit()

    if cas_result.rowcount == 0:
        raise HTTPException(status_code=409, detail="Classification retry already in progress")

    background_tasks.add_task(classify_document_pipeline, document.id, document.file_path)
    return {"message": "Retrying classification", "doc_id": doc_id}
