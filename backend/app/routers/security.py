"""
Security logging router for recording security events.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user
from app import models, schemas
from datetime import datetime, timezone

router = APIRouter(prefix="/security", tags=["security"])


@router.post("/log", response_model=dict)
async def log_security_event(
    log_data: schemas.SecurityLogCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Log a security event (e.g., phone detection, unauthorized person).
    """
    try:
        # Create security log entry
        security_log = models.SecurityLog(
            user_id=current_user.id,
            activity_type=log_data.activity_type,
            timestamp=datetime.now(timezone.utc),
            details=log_data.metadata
        )
        
        db.add(security_log)
        await db.commit()
        await db.refresh(security_log)
        
        return {
            "status": "success",
            "message": "Security event logged successfully",
            "log_id": security_log.id
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log security event: {str(e)}")


@router.get("/logs", response_model=list[schemas.SecurityLogSummary])
async def get_security_logs(
    limit: int | None = None,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve security logs (admin only).
    """
    from app.rbac import require_admin
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    # Only admins can view security logs
    require_admin(current_user)
    
    query = (
        select(models.SecurityLog)
        .options(selectinload(models.SecurityLog.user))
        .order_by(models.SecurityLog.timestamp.desc())
    )
    if limit is not None and limit > 0:
        query = query.limit(limit)

    result = await db.execute(query)
    
    logs = result.scalars().all()
    return logs


@router.get("/access-logs", response_model=list[schemas.AccessLog])
async def get_access_logs(
    limit: int | None = None,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve access logs (admin only).
    """
    from app.rbac import require_admin
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    # Only admins can view access logs
    require_admin(current_user)
    
    query = (
        select(models.AccessLog)
        .options(selectinload(models.AccessLog.user), selectinload(models.AccessLog.document))
        .order_by(models.AccessLog.access_time.desc())
    )
    if limit is not None and limit > 0:
        query = query.limit(limit)

    result = await db.execute(query)
    
    logs = result.scalars().all()
    return logs
