from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from .. import crud, schemas
from ..dependencies import get_current_user
from ..models import User

router = APIRouter()

@router.post("/departments", response_model=schemas.Department)
async def create_department(department: schemas.DepartmentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # For now, allow any authenticated user to create departments; in production, add admin check
    return await crud.create_department(db, department)

@router.get("/departments", response_model=list[schemas.Department])
async def read_departments(db: AsyncSession = Depends(get_db)):
    departments = await crud.get_departments(db)
    return departments
