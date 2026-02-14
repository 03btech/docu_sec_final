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
            details=log_data.metadata,
            image_data=log_data.image_data
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
    limit: int = 50,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve security logs (admin only).
    Returns summaries without image_data to keep payloads small.
    """
    from app.rbac import require_admin
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    # Only admins can view security logs
    require_admin(current_user)
    
    result = await db.execute(
        select(models.SecurityLog)
        .options(selectinload(models.SecurityLog.user))
        .order_by(models.SecurityLog.timestamp.desc())
        .limit(limit)
    )
    
    logs = result.scalars().all()
    # Set has_image flag without returning the full image data
    summaries = []
    for log in logs:
        summary = schemas.SecurityLogSummary.model_validate(log)
        summary.has_image = bool(log.image_data)
        summaries.append(summary)
    return summaries


@router.get("/logs/{log_id}/image", response_model=dict)
async def get_security_log_image(
    log_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the captured camera image for a specific security log (admin only).
    """
    from app.rbac import require_admin
    from sqlalchemy import select
    
    require_admin(current_user)
    
    result = await db.execute(
        select(models.SecurityLog).where(models.SecurityLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Security log not found")
    
    if not log.image_data:
        raise HTTPException(status_code=404, detail="No image available for this log")
    
    return {
        "log_id": log_id,
        "image_data": log.image_data,
        "activity_type": log.activity_type,
        "timestamp": log.timestamp.isoformat()
    }


@router.get("/access-logs", response_model=list[schemas.AccessLog])
async def get_access_logs(
    limit: int = 50,
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
    
    result = await db.execute(
        select(models.AccessLog)
        .options(selectinload(models.AccessLog.user), selectinload(models.AccessLog.document))
        .order_by(models.AccessLog.access_time.desc())
        .limit(limit)
    )
    
    logs = result.scalars().all()
    return logs
