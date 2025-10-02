from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.responses import FileResponse
import os
import shutil
from pathlib import Path
import asyncio
from ..database import get_db, async_session
from .. import crud, models, schemas
from ..dependencies import get_current_user
from ml.classifier import classify_document

router = APIRouter()

UPLOAD_DIR = Path("/app/uploaded_files")
UPLOAD_DIR.mkdir(exist_ok=True)

async def classify_and_update_document(doc_id: int, file_path: str):
    """Background task to classify document and update DB."""
    classification_str = await asyncio.to_thread(classify_document, file_path)
    
    # Map to enum
    try:
        classification = models.ClassificationLevel(classification_str)
    except ValueError:
        classification = models.ClassificationLevel.unclassified

    async with async_session() as db:
        result = await db.execute(select(models.Document).where(models.Document.id == doc_id))
        document = result.scalars().first()
        if document:
            document.classification = classification
            await db.commit()

async def cleanup_orphaned_files():
    """Utility function to clean up files that exist in volume but not in database."""
    try:
        # Get all files in upload directory
        existing_files = set()
        if UPLOAD_DIR.exists():
            for file_path in UPLOAD_DIR.iterdir():
                if file_path.is_file():
                    existing_files.add(str(file_path))

        # Get all file paths from database
        async with async_session() as db:
            result = await db.execute(select(models.Document.file_path))
            db_file_paths = set(row[0] for row in result.fetchall())

        # Find orphaned files
        orphaned_files = existing_files - db_file_paths

        # Delete orphaned files
        deleted_count = 0
        for file_path in orphaned_files:
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                print(f"Warning: Could not delete orphaned file {file_path}: {e}")

        return {"deleted_count": deleted_count, "orphaned_files": list(orphaned_files)}
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return {"error": str(e)}

@router.post("/upload", response_model=schemas.Document)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Save file
    file_path = UPLOAD_DIR / f"{current_user.id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Classify synchronously
    classification_str = await asyncio.to_thread(classify_document, str(file_path))
    
    # Map to enum
    try:
        classification = models.ClassificationLevel(classification_str)
    except ValueError:
        classification = models.ClassificationLevel.unclassified

    # Create document record
    doc_data = schemas.DocumentCreate(filename=file.filename, classification=classification)
    document = await crud.create_document(db, doc_data, current_user.id, str(file_path))

    # If classification failed, add background task to try again
    if classification == models.ClassificationLevel.unclassified:
        background_tasks.add_task(classify_and_update_document, document.id, str(file_path))

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

@router.get("/documents/view/{doc_id}")
async def view_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """View document - returns file content for secure viewing only."""
    # DEBUG: Log the authorization check
    print(f"\n=== VIEW DOCUMENT DEBUG ===")
    print(f"Document ID: {doc_id}")
    print(f"User: {current_user.username} (ID: {current_user.id})")
    print(f"User Department: {current_user.department_id}")
    
    allowed, reason = await crud.authorize_document_action(db, doc_id, current_user, 'view')
    
    print(f"Authorization Result: allowed={allowed}, reason={reason}")
    
    if not allowed:
        print(f"❌ Access DENIED: {reason}")
        raise HTTPException(status_code=403, detail=reason)
    
    document = await crud.get_document(db, doc_id)
    if not document:
        print(f"❌ Document not found in database")
        raise HTTPException(status_code=404, detail="Document not found")

    print(f"Document: {document.filename}")
    print(f"Classification: {document.classification}")
    print(f"Owner ID: {document.owner_id}")
    
    file_path = document.file_path
    print(f"File Path: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found on disk: {file_path}")
        raise HTTPException(status_code=404, detail="File not found on server")

    print(f"✅ Access GRANTED - Returning file")
    print(f"=== END DEBUG ===\n")
    
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
        print(f"Warning: Could not delete file {file_path}: {e}")

    return {"message": "Document deleted"}

@router.post("/admin/cleanup-orphaned-files")
async def cleanup_orphaned_files_endpoint(
    current_user: models.User = Depends(get_current_user)
):
    """Admin endpoint to clean up orphaned files (files without database records)."""
    # Check if user is admin (you might want to add proper admin role checking)
    if not current_user.username == "admin":  # Adjust this condition based on your admin logic
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
